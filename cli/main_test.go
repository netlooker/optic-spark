package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ── downloadImage tests ──────────────────────────────────────────────────────

func TestDownloadImage_Success(t *testing.T) {
	imageData := []byte("fake-png-bytes")

	// Serve the fake image on a test server
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write(imageData) //nolint:errcheck
	}))
	defer srv.Close()

	outDir := t.TempDir()
	url := srv.URL + "/output/test_image.png"

	err := downloadImage(url, outDir)
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}

	// Verify the file was saved with the correct name
	saved := filepath.Join(outDir, "test_image.png")
	data, err := os.ReadFile(saved)
	if err != nil {
		t.Fatalf("expected saved file at %s, got error: %v", saved, err)
	}
	if string(data) != string(imageData) {
		t.Errorf("file contents mismatch: got %q, want %q", data, imageData)
	}
}

func TestDownloadImage_BadStatus(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "not found", http.StatusNotFound)
	}))
	defer srv.Close()

	err := downloadImage(srv.URL+"/output/missing.png", t.TempDir())
	if err == nil {
		t.Fatal("expected an error for 404 response, got nil")
	}
	if !strings.Contains(err.Error(), "bad status") {
		t.Errorf("expected 'bad status' error, got: %v", err)
	}
}

func TestDownloadImage_NetworkError(t *testing.T) {
	err := downloadImage("http://127.0.0.1:1/image.png", t.TempDir())
	if err == nil {
		t.Fatal("expected a network error for unreachable host, got nil")
	}
}

func TestDownloadImage_CreatesOutputDir(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("data")) //nolint:errcheck
	}))
	defer srv.Close()

	// Use a nested path that doesn't exist yet
	outDir := filepath.Join(t.TempDir(), "nested", "dir")

	err := downloadImage(srv.URL+"/output/img.png", outDir)
	if err != nil {
		t.Fatalf("expected dir to be created automatically, got: %v", err)
	}
	if _, err := os.Stat(outDir); os.IsNotExist(err) {
		t.Errorf("expected output dir to be created at %s", outDir)
	}
}

// ── newWebhookHandler tests ──────────────────────────────────────────────────

func postWebhook(t *testing.T, handler http.Handler, payload WebhookPayload) *httptest.ResponseRecorder {
	t.Helper()
	body, _ := json.Marshal(payload)
	req := httptest.NewRequest(http.MethodPost, "/webhook", strings.NewReader(string(body)))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	return rr
}

func TestWebhookHandler_CompletedPayload(t *testing.T) {
	// Serve a fake image so downloadImage succeeds
	imgSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("png-bytes")) //nolint:errcheck
	}))
	defer imgSrv.Close()

	outDir := t.TempDir()
	done := make(chan bool, 1)
	// Pass imgSrv.URL as apiHost so localhost URLs in the payload rewrite correctly.
	handler := newWebhookHandler(done, outDir, imgSrv.URL)

	payload := WebhookPayload{
		JobID:    "abc-123",
		Status:   "completed",
		ImageURL: "http://localhost:7070/output/result.png",
	}

	rr := postWebhook(t, handler, payload)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
	result := <-done
	if !result {
		t.Error("expected done channel to receive true for completed job")
	}
}

func TestWebhookHandler_FailedPayload(t *testing.T) {
	done := make(chan bool, 1)
	handler := newWebhookHandler(done, t.TempDir(), "")

	payload := WebhookPayload{
		JobID:     "abc-456",
		Status:    "failed",
		ErrorCode: "INFERENCE_ERROR",
		ErrorHint: "VRAM OOM",
	}

	rr := postWebhook(t, handler, payload)

	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
	result := <-done
	if result {
		t.Error("expected done channel to receive false for failed job")
	}
}

func TestWebhookHandler_WrongMethod(t *testing.T) {
	done := make(chan bool, 1)
	handler := newWebhookHandler(done, t.TempDir(), "")

	req := httptest.NewRequest(http.MethodGet, "/webhook", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusMethodNotAllowed {
		t.Errorf("expected 405, got %d", rr.Code)
	}
}

func TestWebhookHandler_InvalidJSON(t *testing.T) {
	done := make(chan bool, 1)
	handler := newWebhookHandler(done, t.TempDir(), "")

	req := httptest.NewRequest(http.MethodPost, "/webhook", strings.NewReader("{not-valid-json"))
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rr.Code)
	}
}

func TestWebhookHandler_DownloadFailure(t *testing.T) {
	// Image server that returns 500
	imgSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "server error", http.StatusInternalServerError)
	}))
	defer imgSrv.Close()

	done := make(chan bool, 1)
	handler := newWebhookHandler(done, t.TempDir(), imgSrv.URL)

	payload := WebhookPayload{
		JobID:    "abc-789",
		Status:   "completed",
		ImageURL: imgSrv.URL + "/output/result.png",
	}

	postWebhook(t, handler, payload)

	result := <-done
	if result {
		t.Error("expected done=false when image download fails")
	}
}
