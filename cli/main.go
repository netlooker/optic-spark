package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type GenerateRequest struct {
	WebhookURL   string `json:"webhook_url"`
	Prompt       string `json:"prompt"`
	AspectRatio  string `json:"aspect_ratio"`
	OutputFormat string `json:"output_format"`
}

type WebhookPayload struct {
	JobID     string `json:"job_id"`
	Status    string `json:"status"`
	ImageURL  string `json:"image_url"`
	ErrorCode string `json:"error_code"`
	ErrorHint string `json:"error_hint"`
}

func main() {
	apiHost := flag.String("api", "http://localhost:7070", "Optic-Spark API base URL")
	callbackHost := flag.String("callback-host", "http://host.docker.internal", "Host IP/domain for the API to reach this CLI")
	prompt := flag.String("prompt", "", "Image description (required)")
	aspect := flag.String("aspect", "1:1", "Aspect ratio (16:9, 9:16, 1:1, etc.)")
	format := flag.String("format", "png", "Output format (png, webp, jpeg)")
	outDir := flag.String("out", ".", "Output directory for the saved image")
	flag.Parse()

	if *prompt == "" {
		fmt.Println("Usage of optic-cli:")
		flag.PrintDefaults()
		os.Exit(1)
	}

	// 1. Start ephemeral listener on a random port
	listener, err := net.Listen("tcp", ":0")
	if err != nil {
		log.Fatalf("Failed to bind random port: %v", err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	webhookURL := fmt.Sprintf("%s:%d/webhook", strings.TrimRight(*callbackHost, "/"), port)

	done := make(chan bool)

	// 2. Setup webhook handler
	http.HandleFunc("/webhook", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var payload WebhookPayload
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			http.Error(w, "Bad request", http.StatusBadRequest)
			return
		}

		w.WriteHeader(http.StatusOK)

		if payload.Status == "failed" {
			fmt.Printf("\n❌ Generation failed (Job %s)\n", payload.JobID)
			fmt.Printf("Error: %s - %s\n", payload.ErrorCode, payload.ErrorHint)
			done <- false
			return
		}

		fmt.Printf("\n✅ Image generated successfully! Downloading...\n")
		err := downloadImage(payload.ImageURL, *outDir)
		if err != nil {
			fmt.Printf("❌ Failed to download image: %v\n", err)
			done <- false
			return
		}

		done <- true
	})

	go func() {
		if err := http.Serve(listener, nil); err != nil {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	// 3. Dispatch generation request
	reqPayload := GenerateRequest{
		WebhookURL:   webhookURL,
		Prompt:       *prompt,
		AspectRatio:  *aspect,
		OutputFormat: *format,
	}

	bodyBytes, _ := json.Marshal(reqPayload)
	endpoint := fmt.Sprintf("%s/generate", strings.TrimRight(*apiHost, "/"))
	
	fmt.Printf("🚀 Dispatching request to %s...\n", endpoint)
	fmt.Printf("📡 Listening for webhook on %s...\n", webhookURL)

	resp, err := http.Post(endpoint, "application/json", bytes.NewBuffer(bodyBytes))
	if err != nil {
		log.Fatalf("❌ Failed to contact API: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		log.Fatalf("❌ API rejected request (Status %d): %s", resp.StatusCode, string(body))
	}

	fmt.Printf("⏳ Waiting for Grace-Blackwell inference...\n")

	// 4. Block until webhook is received
	success := <-done
	if !success {
		os.Exit(1)
	}
	fmt.Println("🎉 All done!")
}

func downloadImage(url, outDir string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	// Extract filename from URL
	parts := strings.Split(url, "/")
	filename := parts[len(parts)-1]
	
	os.MkdirAll(outDir, 0755)
	filepath := filepath.Join(outDir, filename)

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return err
	}

	fmt.Printf("💾 Saved to: %s\n", filepath)
	return nil
}
