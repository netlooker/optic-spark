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
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

// GenerateRequest is the payload sent to the Optic-Spark /generate endpoint.
type GenerateRequest struct {
	WebhookURL   string `json:"webhook_url"`
	Prompt       string `json:"prompt"`
	AspectRatio  string `json:"aspect_ratio"`
	OutputFormat string `json:"output_format"`
}

// WebhookPayload is the callback payload delivered by the Optic-Spark worker.
type WebhookPayload struct {
	JobID     string `json:"job_id"`
	Status    string `json:"status"`
	ImageURL  string `json:"image_url"`
	ErrorCode string `json:"error_code"`
	ErrorHint string `json:"error_hint"`
}

// rewriteLocalhostURL replaces localhost/127.0.0.1 in a URL with the
// actual API host so the CLI can download images even when BASE_URL is
// not configured on the server (common during initial setup).
func rewriteLocalhostURL(imageURL, apiHost string) string {
	if apiHost == "" {
		return imageURL
	}
	parsed, err := url.Parse(imageURL)
	if err != nil {
		return imageURL
	}
	h := parsed.Hostname()
	if h == "localhost" || h == "127.0.0.1" {
		// Keep just the path (+ query), swap the host with apiHost.
		return strings.TrimRight(apiHost, "/") + parsed.RequestURI()
	}
	return imageURL
}

// newWebhookHandler returns an http.HandlerFunc that decodes the webhook
// payload and signals the done channel. apiHost is used to rewrite localhost
// image URLs in case BASE_URL is not configured on the server.
func newWebhookHandler(done chan bool, outDir, apiHost string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
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

		// Rewrite localhost URLs so we can download from the remote DGX.
		imageURL := rewriteLocalhostURL(payload.ImageURL, apiHost)

		err := downloadImage(imageURL, outDir)
		if err != nil {
			fmt.Printf("❌ Failed to download image: %v\n", err)
			done <- false
			return
		}

		done <- true
	}
}

// downloadImage fetches the image at url and writes it into outDir,
// using the filename component of the URL.
func downloadImage(url, outDir string) error {
	resp, err := http.Get(url) //nolint:gosec // url is from trusted API webhook
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

	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("failed to create output dir: %w", err)
	}

	dst := filepath.Join(outDir, filename)
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	if _, err = io.Copy(out, resp.Body); err != nil {
		return err
	}

	fmt.Printf("💾 Saved to: %s\n", dst)
	return nil
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

	// 2. Setup webhook handler and start server
	mux := http.NewServeMux()
	mux.HandleFunc("/webhook", newWebhookHandler(done, *outDir, strings.TrimRight(*apiHost, "/")))

	go func() {
		if err := http.Serve(listener, mux); err != nil {
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

	resp, err := http.Post(endpoint, "application/json", bytes.NewBuffer(bodyBytes)) //nolint:gosec
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
