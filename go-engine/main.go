package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"html"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

type SourceConfig struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	NameFa string `json:"name_fa"`
	Type   string `json:"type"` // "twitter", "telegram", "rss"
	Target string `json:"target"`
	Avatar string `json:"avatar"`
	RTL    bool   `json:"rtl"`
}

type ArticleItem struct {
	Hash           string   `json:"hash"`
	SourceID       string   `json:"source_id"`
	SourceName     string   `json:"source_name"`
	SourceNameFa   string   `json:"source_name_fa"`
	SourceType     string   `json:"source_type"`
	AuthorHandle   string   `json:"author_handle"`
	Title          string   `json:"title"`
	Summary        string   `json:"summary"`
	FullBody       string   `json:"full_body"`
	Link           string   `json:"link"`
	ArticleRelPath string   `json:"article_rel_path"`
	MediaFiles     []string `json:"media_files"`
	PublishedAt    string   `json:"published_at"`
	PublishedEpoch int64    `json:"published_epoch"`
	RTL            bool     `json:"rtl"`
}

type StateData struct {
	SeenHashes []string `json:"seen_hashes"`
	LastRunUTC string   `json:"last_run_utc"`
}

var (
	reStripTags   = regexp.MustCompile(`<[^>]+>`)
	reCleanSpaces = regexp.MustCompile(`\s+`)
	reTgPostBlock = regexp.MustCompile(`(?s)<div class="tgme_widget_message\s+[^"]*js-widget_message[^"]*"\s+data-post="([^"]+)".*?</div>\s*</div>\s*</div>`)
	reTgText      = regexp.MustCompile(`(?s)<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>`)
	reTgTime      = regexp.MustCompile(`<time[^>]*datetime="([^"]+)"`)
	reTgPhoto     = regexp.MustCompile(`background-image:url\('([^']+)'\)`)
	reParagraph   = regexp.MustCompile(`(?s)<p[^>]*>(.*?)</p>`)

	stripTagsList = []*regexp.Regexp{
		regexp.MustCompile(`(?s)<script[^>]*>.*?</script>`),
		regexp.MustCompile(`(?s)<style[^>]*>.*?</style>`),
		regexp.MustCompile(`(?s)<nav[^>]*>.*?</nav>`),
		regexp.MustCompile(`(?s)<footer[^>]*>.*?</footer>`),
		regexp.MustCompile(`(?s)<header[^>]*>.*?</header>`),
		regexp.MustCompile(`(?s)<aside[^>]*>.*?</aside>`),
		regexp.MustCompile(`(?s)<noscript[^>]*>.*?</noscript>`),
	}

	client = &http.Client{
		Timeout: 10 * time.Second,
	}

	tehranLoc = time.FixedZone("IRST", 3*3600+1800)
)

var sources = []SourceConfig{
	// 12 Twitter Accounts
	{"tw_sharifizarchi", "Ali Sharifi Zarchi", "دکتر علی شریفی زارچی", "twitter", "SharifiZarchi", "https://unavatar.io/twitter/SharifiZarchi", true},
	{"tw_thetwelfth_imam", "The Twelfth Imam", "مهدی پرپنچی", "twitter", "thetwelfth_Imam", "https://unavatar.io/twitter/thetwelfth_Imam", true},
	{"tw_usabehfarsi", "USA BehFarsi", "وزارت خارجه آمریکا به فارسی", "twitter", "USABehFarsi", "https://unavatar.io/twitter/USABehFarsi", true},
	{"tw_souzangar", "Nima Souzangar", "نیما سوزنگر", "twitter", "souzangar", "https://unavatar.io/twitter/souzangar", true},
	{"tw_bookunt", "Hossein Derakhshan", "حسین درخشان", "twitter", "bookunt", "https://unavatar.io/twitter/bookunt", true},
	{"tw_tom_doerr", "Tom Doerr", "تام دور", "twitter", "tom_doerr", "https://unavatar.io/twitter/tom_doerr", false},
	{"tw_matinsenpai", "Matin SenPai", "متین سنپای", "twitter", "MatinSenPai", "https://unavatar.io/twitter/MatinSenPai", true},
	{"tw_patterniha", "Patterniha", "الگوها", "twitter", "patterniha", "https://unavatar.io/twitter/patterniha", true},
	{"tw_mitrahejazipour", "Mitra Hejazipour", "میترا حجازی‌پور", "twitter", "MitraHejazipour", "https://unavatar.io/twitter/MitraHejazipour", true},
	{"tw_edaalateali", "Edaalate Ali", "عدالت علی", "twitter", "EdaalateAli1400", "https://unavatar.io/twitter/EdaalateAli1400", true},
	{"tw_realdonaldtrump", "Donald J. Trump", "دونالد ترامپ", "twitter", "realDonaldTrump", "https://unavatar.io/twitter/realDonaldTrump", false},
	{"tw_pahlavicomms", "Pahlavi Comms", "دفتر ارتباطات شاهزاده رضا پهلوی", "twitter", "PahlaviComms", "https://unavatar.io/twitter/PahlaviComms", true},

	// 12 Telegram Channels
	{"tg_linuxor", "Linuxor", "لینوکسور", "telegram", "Linuxor", "", true},
	{"tg_jadivarlog", "Jadi", "جادی تی‌وی", "telegram", "jadivarlog", "", true},
	{"tg_rezapahlavi", "Official Reza Pahlavi", "شاهزاده رضا پهلوی", "telegram", "OfficialRezaPahlavi", "", true},
	{"tg_iranintltv", "Iran International", "ایران اینترنشنال", "telegram", "IranintlTV", "", true},
	{"tg_vahidonline", "Vahid Online", "وحید آنلاین", "telegram", "VahidOnline", "", true},
	{"tg_matinsenpaii", "Matin SenPaii", "کانال متین سنپای", "telegram", "MatinSenPaii", "", true},
	{"tg_edaalateali_dark", "Edaalate Ali Dark", "عدالت علی دارک", "telegram", "EdaalateAli1400_Dark", "", true},
	{"tg_patt_channel", "Patt Channel X", "کانال الگوها", "telegram", "patt_channel_x", "", true},
	{"tg_m4tinbeigi", "Matin Beigi", "متین بیگی", "telegram", "M4tinBeigi", "", true},
	{"tg_rostamchannel", "Rostam Channel", "رستم مدیا", "telegram", "Rostamchannel", "", true},
	{"tg_ircfspace", "IRCF Space", "آی‌آر سی‌اف (فیلترشکن و کلودفلر)", "telegram", "ircfspace", "", true},
	{"tg_whitedns", "White DNS", "وایت دی‌ان‌اس", "telegram", "whitedns", "", true},

	// 8 Global & Persian RSS Feeds
	{"rss_bbc", "BBC Persian", "بی‌بی‌سی فارسی", "rss", "https://feeds.bbci.co.uk/persian/rss.xml", "", true},
	{"rss_farda", "Radio Farda", "رادیو فردا", "rss", "https://www.radiofarda.com/api/zrttpol-vomx-tpeoogpi", "", true},
	{"rss_iranintl", "Iran International Wire", "ایران اینترنشنال وب", "rss", "https://www.iranintl.com/feed", "", true},
	{"rss_euronews", "Euronews Persian", "یورونیوز فارسی", "rss", "https://fa.euronews.com/rss", "", true},
	{"rss_dw", "DW Persian", "دویچه‌وله فارسی", "rss", "https://rss.dw.com/xml/rss-per-all", "", true},
	{"rss_reuters", "Reuters Wire", "خبرگزاری رویترز", "rss", "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en", "", false},
	{"rss_ap", "AP News Wire", "اسوشیتد پرس", "rss", "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en", "", false},
	{"rss_hackernews", "Hacker News", "هکر نیوز (تکنولوژی)", "rss", "https://hnrss.org/frontpage", "", false},
}

func main() {
	startTime := time.Now()
	nowUTC := time.Now().UTC()
	dateFolder := nowUTC.Format("2006-01-02")
	timeStrTehran := nowUTC.In(tehranLoc).Format("2006-01-02 15:04 IRST")

	baseDir, _ := filepath.Abs(".")
	if filepath.Base(baseDir) == "go-engine" {
		baseDir = filepath.Dir(baseDir)
	}

	newsDir := filepath.Join(baseDir, "news")
	mediaDir := filepath.Join(baseDir, "media", dateFolder)
	articlesDir := filepath.Join(baseDir, "articles", dateFolder)
	publicDir := filepath.Join(baseDir, "public")
	stateFile := filepath.Join(baseDir, "state.json")

	_ = os.MkdirAll(newsDir, 0755)
	_ = os.MkdirAll(mediaDir, 0755)
	_ = os.MkdirAll(articlesDir, 0755)
	_ = os.MkdirAll(publicDir, 0755)

	fmt.Printf("=== High-Performance Go News & Media Engine ===\n")
	fmt.Printf("Execution time: %s | Timezone: %s\n", nowUTC.Format(time.RFC3339), timeStrTehran)

	// Load state
	state := loadState(stateFile)
	seenMap := make(map[string]bool)
	for _, h := range state.SeenHashes {
		seenMap[h] = true
	}
	fmt.Printf("Loaded %d previously seen hashes from state.json\n", len(state.SeenHashes))

	// Concurrently fetch sources with worker pool
	var (
		wg         sync.WaitGroup
		sem        = make(chan struct{}, 6) // max 6 concurrent
		mu         sync.Mutex
		allFetched []ArticleItem
	)

	for _, src := range sources {
		wg.Add(1)
		go func(s SourceConfig) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			items := fetchSource(s, baseDir, dateFolder)
			if len(items) > 0 {
				mu.Lock()
				allFetched = append(allFetched, items...)
				mu.Unlock()
			}
		}(src)
	}
	wg.Wait()

	fmt.Printf("Total items fetched across 32 sources: %d\n", len(allFetched))

	// Sort newest first
	sort.Slice(allFetched, func(i, j int) bool {
		return allFetched[i].PublishedEpoch > allFetched[j].PublishedEpoch
	})

	// Deduplication & Full Article Extraction
	var newItems []ArticleItem
	var newHashes []string

	for i := range allFetched {
		item := &allFetched[i]
		relPath := fmt.Sprintf("articles/%s/%s.md", dateFolder, item.Hash)
		fullPath := filepath.Join(baseDir, relPath)
		if _, err := os.Stat(fullPath); err == nil {
			item.ArticleRelPath = relPath
		}

		if !seenMap[item.Hash] {
			seenMap[item.Hash] = true
			newHashes = append(newHashes, item.Hash)

			// If it's an RSS news article, fetch full content!
			if item.SourceType == "rss" && item.Link != "" && !strings.Contains(item.Link, "news.google.com") {
				fullText := extractFullArticle(item.Link)
				if len(fullText) > 200 {
					item.FullBody = fullText
				}
			}

			// Archive full article to disk if full body exists
			if item.FullBody != "" {
				artRelPath := saveArticleToDisk(baseDir, dateFolder, item)
				item.ArticleRelPath = artRelPath
			}

			newItems = append(newItems, *item)
		}
	}

	fmt.Printf("New items in this 30-min window: %d\n", len(newItems))

	// Download media for items (deduplicated)
	downloadMediaForItems(baseDir, dateFolder, allFetched)

	// Generate Artifacts
	intervalFile := fmt.Sprintf("%02d-%02d.md", nowUTC.Hour(), (nowUTC.Minute()/30)*30)
	intervalDir := filepath.Join(newsDir, dateFolder)
	_ = os.MkdirAll(intervalDir, 0755)
	saveMarkdownFile(filepath.Join(intervalDir, intervalFile), generateDigestMarkdown(nowUTC, timeStrTehran, allFetched, true))

	saveMarkdownFile(filepath.Join(newsDir, "latest.md"), generateDigestMarkdown(nowUTC, timeStrTehran, allFetched, false))
	saveMarkdownFile(filepath.Join(baseDir, "index.md"), generateRootIndex(nowUTC, timeStrTehran, allFetched))

	saveJSONFile(filepath.Join(publicDir, "latest.json"), map[string]interface{}{
		"generated_at_utc":    nowUTC.Format(time.RFC3339),
		"generated_at_tehran": timeStrTehran,
		"total_articles":      len(allFetched),
		"articles":            allFetched,
	})

	saveHTMLFile(filepath.Join(publicDir, "index.html"), generateHighFidelityDashboard(nowUTC, timeStrTehran, allFetched))

	// Update state
	state.SeenHashes = append(state.SeenHashes, newHashes...)
	if len(state.SeenHashes) > 10000 {
		state.SeenHashes = state.SeenHashes[len(state.SeenHashes)-10000:]
	}
	state.LastRunUTC = nowUTC.Format(time.RFC3339)
	saveState(stateFile, state)

	fmt.Printf("=== Go Engine finished cleanly in %v ===\n", time.Since(startTime))
}

func fetchSource(src SourceConfig, baseDir, dateFolder string) []ArticleItem {
	switch src.Type {
	case "telegram":
		return fetchTelegram(src)
	case "twitter":
		return fetchTwitter(src)
	case "rss":
		return fetchRSS(src)
	}
	return nil
}

func fetchTelegram(src SourceConfig) []ArticleItem {
	url := fmt.Sprintf("https://t.me/s/%s", src.Target)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	content := string(body)

	blocks := reTgPostBlock.FindAllStringSubmatch(content, -1)
	var items []ArticleItem

	for _, b := range blocks {
		postID := b[1]
		blockHtml := b[0]

		textMatch := reTgText.FindStringSubmatch(blockHtml)
		rawText := ""
		if len(textMatch) > 1 {
			rawText = textMatch[1]
		}
		cleanText := cleanHTML(rawText)

		timeMatch := reTgTime.FindStringSubmatch(blockHtml)
		dtStr := ""
		epoch := time.Now().Unix()
		if len(timeMatch) > 1 {
			dtStr = timeMatch[1]
			if t, err := time.Parse(time.RFC3339, dtStr); err == nil {
				epoch = t.Unix()
			}
		}

		var mediaUrls []string
		photos := reTgPhoto.FindAllStringSubmatch(blockHtml, -1)
		for _, p := range photos {
			if len(p) > 1 && strings.HasPrefix(p[1], "http") {
				mediaUrls = append(mediaUrls, p[1])
			}
		}

		if len(cleanText) > 10 || len(mediaUrls) > 0 {
			itemHash := hashString(fmt.Sprintf("%s|%s", postID, cleanText[:min(len(cleanText), 40)]))
			title := cleanText
			if len(title) > 90 {
				title = title[:87] + "..."
			}
			items = append(items, ArticleItem{
				Hash:           itemHash,
				SourceID:       src.ID,
				SourceName:     src.Name,
				SourceNameFa:   src.NameFa,
				SourceType:     "telegram",
				AuthorHandle:   "@" + src.Target,
				Title:          title,
				Summary:        cleanText,
				FullBody:       cleanText,
				Link:           fmt.Sprintf("https://t.me/%s", postID),
				MediaFiles:     mediaUrls,
				PublishedAt:    dtStr,
				PublishedEpoch: epoch,
				RTL:            src.RTL,
			})
		}
	}
	if len(items) > 8 {
		items = items[len(items)-8:]
	}
	return items
}

func fetchTwitter(src SourceConfig) []ArticleItem {
	url := fmt.Sprintf("https://news.google.com/rss/search?q=site:x.com/%s+OR+site:twitter.com/%s&hl=fa&gl=IR&ceid=IR:fa", src.Target, src.Target)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0")
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	type RSSItem struct {
		Title   string `xml:"title"`
		Link    string `xml:"link"`
		PubDate string `xml:"pubDate"`
	}
	type RSSFeed struct {
		Channel struct {
			Items []RSSItem `xml:"item"`
		} `xml:"channel"`
	}

	var feed RSSFeed
	if err := xml.NewDecoder(resp.Body).Decode(&feed); err != nil {
		return nil
	}

	var items []ArticleItem
	for _, it := range feed.Channel.Items {
		cleanTitle := cleanHTML(it.Title)
		cleanTitle = strings.TrimSuffix(cleanTitle, fmt.Sprintf(" - %s on X", src.Target))
		epoch := time.Now().Unix()
		if t, err := time.Parse(time.RFC1123Z, it.PubDate); err == nil {
			epoch = t.Unix()
		} else if t, err := time.Parse(time.RFC1123, it.PubDate); err == nil {
			epoch = t.Unix()
		}

		h := hashString(fmt.Sprintf("%s|%s", src.Target, cleanTitle))
		items = append(items, ArticleItem{
			Hash:           h,
			SourceID:       src.ID,
			SourceName:     src.Name,
			SourceNameFa:   src.NameFa,
			SourceType:     "twitter",
			AuthorHandle:   "@" + src.Target,
			Title:          cleanTitle,
			Summary:        cleanTitle,
			FullBody:       cleanTitle,
			Link:           it.Link,
			PublishedAt:    it.PubDate,
			PublishedEpoch: epoch,
			RTL:            src.RTL,
		})
		if len(items) >= 8 {
			break
		}
	}
	return items
}

func fetchRSS(src SourceConfig) []ArticleItem {
	req, _ := http.NewRequest("GET", src.Target, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsResilienceBot/2.0")
	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	type RSSItem struct {
		Title       string `xml:"title"`
		Link        string `xml:"link"`
		Description string `xml:"description"`
		PubDate     string `xml:"pubDate"`
		Date        string `xml:"date"`
	}
	type RSSDoc struct {
		Channel struct {
			Items []RSSItem `xml:"item"`
		} `xml:"channel"`
	}

	var doc RSSDoc
	if err := xml.NewDecoder(resp.Body).Decode(&doc); err != nil {
		return nil
	}

	var items []ArticleItem
	for _, it := range doc.Channel.Items {
		title := cleanHTML(it.Title)
		desc := cleanHTML(it.Description)
		link := strings.TrimSpace(it.Link)
		if title == "" || link == "" {
			continue
		}

		dateStr := it.PubDate
		if dateStr == "" {
			dateStr = it.Date
		}
		epoch := time.Now().Unix()
		if t, err := time.Parse(time.RFC1123Z, dateStr); err == nil {
			epoch = t.Unix()
		} else if t, err := time.Parse(time.RFC1123, dateStr); err == nil {
			epoch = t.Unix()
		}

		h := hashString(fmt.Sprintf("%s|%s", title, link))
		items = append(items, ArticleItem{
			Hash:           h,
			SourceID:       src.ID,
			SourceName:     src.Name,
			SourceNameFa:   src.NameFa,
			SourceType:     "rss",
			Title:          title,
			Summary:        desc,
			FullBody:       desc,
			Link:           link,
			PublishedAt:    dateStr,
			PublishedEpoch: epoch,
			RTL:            src.RTL,
		})
		if len(items) >= 12 {
			break
		}
	}
	return items
}

func extractFullArticle(url string) string {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return ""
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	resp, err := client.Do(req)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return ""
	}
	htmlStr := string(bodyBytes)
	cleaned := htmlStr
	for _, r := range stripTagsList {
		cleaned = r.ReplaceAllString(cleaned, "")
	}

	matches := reParagraph.FindAllStringSubmatch(cleaned, -1)
	var paras []string
	for _, m := range matches {
		if len(m) > 1 {
			pText := cleanHTML(m[1])
			if len(pText) > 40 {
				paras = append(paras, pText)
			}
		}
	}
	return strings.Join(paras, "\n\n")
}

func saveArticleToDisk(baseDir, dateFolder string, it *ArticleItem) string {
	artDir := filepath.Join(baseDir, "articles", dateFolder)
	_ = os.MkdirAll(artDir, 0755)

	relPath := fmt.Sprintf("articles/%s/%s.md", dateFolder, it.Hash)
	mdPath := filepath.Join(baseDir, relPath)
	htmlPath := filepath.Join(baseDir, fmt.Sprintf("articles/%s/%s.html", dateFolder, it.Hash))

	dirAttr := "rtl"
	alignAttr := "right"
	if !it.RTL {
		dirAttr = "ltr"
		alignAttr = "left"
	}

	var md strings.Builder
	md.WriteString(fmt.Sprintf("# %s\n\n", it.Title))
	md.WriteString(fmt.Sprintf("> منبع: **%s** | تاریخ: `%s`\n\n", it.SourceNameFa, it.PublishedAt))
	if it.Link != "" {
		md.WriteString(fmt.Sprintf("🔗 [مشاهده پیوند اصلی](%s)\n\n", it.Link))
	}
	md.WriteString("---\n\n")
	md.WriteString(it.FullBody)
	md.WriteString("\n\n---\n*ذخیره‌شده برای مطالعه آفلاین در شرایط قطع اینترنت*\n")
	_ = os.WriteFile(mdPath, []byte(md.String()), 0644)

	var doc strings.Builder
	doc.WriteString(fmt.Sprintf(`<!DOCTYPE html>
<html lang="fa" dir="%s">
<head>
  <meta charset="UTF-8">
  <title>%s</title>
  <style>
    body { background: #000000; color: #e7e9ea; font-family: -apple-system, Tahoma, sans-serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 24px; text-align: %s; }
    h1 { color: #ffffff; font-size: 1.6rem; border-bottom: 1px solid #2f3336; padding-bottom: 12px; margin-bottom: 12px; }
    .meta { color: #71767b; font-size: 0.9rem; margin-bottom: 24px; }
    p { margin-bottom: 16px; font-size: 1.05rem; }
    a { color: #1d9bf0; text-decoration: none; }
    .back { display: inline-block; margin-bottom: 20px; padding: 6px 14px; background: #16181c; border-radius: 6px; border: 1px solid #2f3336; color: #1d9bf0; }
  </style>
</head>
<body>
  <a class="back" href="../../public/index.html">← بازگشت به پیشخوان اصلی</a>
  <h1>%s</h1>
  <div class="meta">منبع: <strong>%s</strong> | زمان: %s</div>
  <article>
`, dirAttr, html.EscapeString(it.Title), alignAttr, html.EscapeString(it.Title), html.EscapeString(it.SourceNameFa), html.EscapeString(it.PublishedAt)))

	for _, p := range strings.Split(it.FullBody, "\n\n") {
		p = strings.TrimSpace(p)
		if p != "" {
			doc.WriteString(fmt.Sprintf("    <p>%s</p>\n", html.EscapeString(p)))
		}
	}
	doc.WriteString(`  </article>
</body>
</html>`)
	_ = os.WriteFile(htmlPath, []byte(doc.String()), 0644)

	return relPath
}

func downloadMediaForItems(baseDir, dateFolder string, items []ArticleItem) {
	mediaDir := filepath.Join(baseDir, "media", dateFolder)
	_ = os.MkdirAll(mediaDir, 0755)

	var wg sync.WaitGroup
	sem := make(chan struct{}, 5)
	downloadCount := 0

	for i := range items {
		it := &items[i]
		var localPaths []string
		for _, u := range it.MediaFiles {
			if !strings.HasPrefix(u, "http") {
				continue
			}
			imgHash := hashString(u)[:16]
			fileName := fmt.Sprintf("%s.jpg", imgHash)
			filePath := filepath.Join(mediaDir, fileName)
			relPath := fmt.Sprintf("media/%s/%s", dateFolder, fileName)

			localPaths = append(localPaths, relPath)

			if _, err := os.Stat(filePath); err == nil {
				continue
			}

			if downloadCount >= 25 {
				continue
			}
			downloadCount++

			wg.Add(1)
			go func(srcUrl, destPath string) {
				defer wg.Done()
				sem <- struct{}{}
				defer func() { <-sem }()

				req, err := http.NewRequest("GET", srcUrl, nil)
				if err != nil {
					return
				}
				req.Header.Set("User-Agent", "Mozilla/5.0")
				resp, err := client.Do(req)
				if err != nil || resp.StatusCode != 200 {
					return
				}
				defer resp.Body.Close()

				out, err := os.Create(destPath)
				if err != nil {
					return
				}
				defer out.Close()
				_, _ = io.Copy(out, resp.Body)
			}(u, filePath)
		}
		it.MediaFiles = localPaths
	}
	wg.Wait()
}

func generateDigestMarkdown(nowUTC time.Time, timeStrTehran string, items []ArticleItem, isInterval bool) string {
	var sb strings.Builder
	title := "⚡ آخرین اخبار و رویدادهای لحظه‌ای (Latest Full Digest)"
	if isInterval {
		title = fmt.Sprintf("📡 بولتن ساعت %02d:%02d UTC (%s)", nowUTC.Hour(), (nowUTC.Minute()/30)*30, timeStrTehran)
	}

	sb.WriteString(fmt.Sprintf("# %s\n\n", title))
	sb.WriteString(fmt.Sprintf("> زمان استخراج: **%s** | **متن کامل و کاملاً آفلاین**\n\n---\n\n", timeStrTehran))

	twItems := filterItemsByType(items, "twitter")
	tgItems := filterItemsByType(items, "telegram")
	rssItems := filterItemsByType(items, "rss")

	sb.WriteString("## 🐦 گزیده آخرین توییت‌های مهم (Twitter / X)\n\n")
	for _, it := range twItems[:min(len(twItems), 15)] {
		sb.WriteString(fmt.Sprintf("### %s (`%s`) — *%s*\n", it.SourceNameFa, it.AuthorHandle, it.PublishedAt))
		sb.WriteString(fmt.Sprintf("%s\n\n", it.FullBody))
		if len(it.MediaFiles) > 0 {
			sb.WriteString(fmt.Sprintf("![عکس](%s)\n\n", it.MediaFiles[0]))
		}
		sb.WriteString(fmt.Sprintf("🔗 [مشاهده در توییتر](%s)\n\n---\n\n", it.Link))
	}

	sb.WriteString("## 📱 آخرین پست‌های تلگرام (Telegram Channels)\n\n")
	for _, it := range tgItems[:min(len(tgItems), 15)] {
		sb.WriteString(fmt.Sprintf("### کانال %s (`%s`) — *%s*\n", it.SourceNameFa, it.AuthorHandle, it.PublishedAt))
		sb.WriteString(fmt.Sprintf("%s\n\n", it.FullBody))
		if len(it.MediaFiles) > 0 {
			sb.WriteString(fmt.Sprintf("![عکس](%s)\n\n", it.MediaFiles[0]))
		}
		sb.WriteString(fmt.Sprintf("🔗 [پیوند به تلگرام](%s)\n\n---\n\n", it.Link))
	}

	sb.WriteString("## 📰 گزارش‌های تفصیلی خبرگزاری‌ها (Full Offline Articles)\n\n")
	for _, it := range rssItems[:min(len(rssItems), 15)] {
		sb.WriteString(fmt.Sprintf("### [%s](%s) — `%s`\n", it.Title, it.Link, it.SourceNameFa))
		if it.ArticleRelPath != "" {
			linkPath := it.ArticleRelPath
			if isInterval {
				linkPath = "../../" + it.ArticleRelPath
			} else {
				linkPath = "../" + it.ArticleRelPath
			}
			sb.WriteString(fmt.Sprintf("📖 **[مطالعه متن کامل مقاله به‌صورت آفلاین](%s)**\n\n", linkPath))
		}
		sb.WriteString(fmt.Sprintf("> %s\n\n---\n\n", it.Summary))
	}

	return sb.String()
}

func generateRootIndex(nowUTC time.Time, timeStrTehran string, items []ArticleItem) string {
	var sb strings.Builder
	sb.WriteString("# 🌐 پایگاه مقاومت دیجیتال: رصدخانه جامع اخبار و رسانه‌ها\n\n")
	sb.WriteString(fmt.Sprintf("⏱ **وضعیت سیستم:** موتور بهینه Go فعال | **آخرین به‌روزرسانی:** `%s`\n\n", timeStrTehran))
	sb.WriteString("> این پایگاه متن و رسانه‌های ۳۲ منبع مستقل (توییتر، تلگرام، خبرگزاری‌ها) را هر ۳۰ دقیقه استخراج کرده و به‌صورت کامل برای **مطالعه در شرایط قطع اینترنت** در مخزن ذخیره می‌کند.\n\n")
	sb.WriteString("### 🚀 دسترسی‌های سریع:\n")
	sb.WriteString("- 🌐 [مشاهده پیشخوان مدرن تحت وب (HTML)](public/index.html)\n")
	sb.WriteString("- ⚡ [خلاصه لحظه‌ای متن خام (news/latest.md)](news/latest.md)\n")
	sb.WriteString("- 📂 آرشیو مقالات کامل استخراج‌شده در پوشه `articles/`\n\n---\n\n")

	sb.WriteString("## 🔥 آخرین رویدادهای رصدشده در این ساعت\n\n")
	for i, it := range items[:min(len(items), 15)] {
		typeIcon := "📰"
		if it.SourceType == "twitter" {
			typeIcon = "🐦"
		} else if it.SourceType == "telegram" {
			typeIcon = "📱"
		}
		sb.WriteString(fmt.Sprintf("%d. %s **[%s]** %s", i+1, typeIcon, it.SourceNameFa, it.Title))
		if it.ArticleRelPath != "" {
			sb.WriteString(fmt.Sprintf(" — 📖 [متن کامل آفلاین](%s)", it.ArticleRelPath))
		}
		sb.WriteString("\n")
	}
	return sb.String()
}

func generateHighFidelityDashboard(nowUTC time.Time, timeStrTehran string, items []ArticleItem) string {
	jsonBytes, _ := json.Marshal(items)

	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>رصدخانه جامع اخبار و شبکه‌های اجتماعی | مقاومت دیجیتال</title>
  <style>
    :root {
      --bg: #000000;
      --card-bg: #16181c;
      --border: #2f3336;
      --text: #e7e9ea;
      --text-muted: #71767b;
      --twitter-blue: #1d9bf0;
      --telegram-blue: #24A1DE;
      --accent: #00ba7c;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Tahoma, sans-serif; line-height: 1.6; }
    .layout { max-width: 720px; margin: 0 auto; border-left: 1px solid var(--border); border-right: 1px solid var(--border); min-height: 100vh; }
    
    header { position: sticky; top: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); padding: 14px 20px; z-index: 100; }
    header h1 { font-size: 1.25rem; font-weight: 700; color: #fff; }
    .meta-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }

    .nav-tabs { display: flex; border-bottom: 1px solid var(--border); }
    .tab-btn { flex: 1; text-align: center; padding: 14px; background: none; border: none; color: var(--text-muted); font-size: 0.95rem; font-weight: 600; cursor: pointer; transition: 0.2s; position: relative; }
    .tab-btn.active { color: #fff; }
    .tab-btn.active::after { content: ""; position: absolute; bottom: 0; left: 25%%; width: 50%%; height: 4px; background: var(--twitter-blue); border-radius: 999px; }

    .feed-container { padding-bottom: 80px; }

    /* Card styling */
    .tweet-card { border-bottom: 1px solid var(--border); padding: 16px 20px; display: flex; gap: 14px; transition: background 0.15s; }
    .tweet-card:hover { background: rgba(255,255,255,0.03); }
    .avatar { width: 44px; height: 44px; border-radius: 50%%; background: #2f3336; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #fff; font-size: 1.1rem; overflow: hidden; }
    .tweet-content { flex: 1; min-width: 0; }
    .tweet-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
    .author-name { font-weight: 700; color: #fff; font-size: 0.95rem; }
    .author-handle { color: var(--text-muted); font-size: 0.9rem; direction: ltr; }
    .dot { color: var(--text-muted); }
    .time-badge { color: var(--text-muted); font-size: 0.85rem; }
    .badge-src { font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; background: rgba(29, 155, 240, 0.15); color: var(--twitter-blue); }
    .badge-tg { background: rgba(36, 161, 222, 0.15); color: var(--telegram-blue); }
    .badge-rss { background: rgba(0, 186, 124, 0.15); color: var(--accent); }

    .tweet-text { font-size: 0.98rem; line-height: 1.6; word-wrap: break-word; white-space: pre-line; margin-bottom: 10px; }
    .media-grid { margin-top: 10px; border-radius: 14px; overflow: hidden; border: 1px solid var(--border); }
    .media-grid img { width: 100%%; max-height: 480px; object-fit: cover; display: block; }

    .offline-article-btn { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; padding: 6px 14px; background: #21262d; border: 1px solid #30363d; color: var(--accent); border-radius: 6px; font-size: 0.85rem; text-decoration: none; cursor: pointer; }
    .offline-article-btn:hover { background: #30363d; }

    /* Modal for reading full article */
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(4px); z-index: 999; display: none; align-items: center; justify-content: center; padding: 16px; }
    .modal.open { display: flex; }
    .modal-box { background: #16181c; border: 1px solid var(--border); border-radius: 12px; width: 100%%; max-width: 700px; max-height: 85vh; overflow-y: auto; padding: 28px; position: relative; }
    .modal-close { position: absolute; top: 16px; left: 16px; background: none; border: none; color: #fff; font-size: 1.4rem; cursor: pointer; }
    .modal-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 12px; color: #fff; }
    .modal-meta { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
    .modal-body { font-size: 1.05rem; line-height: 1.8; color: var(--text); }
    .modal-body p { margin-bottom: 16px; }
  </style>
</head>
<body>
  <div class="layout">
    <header>
      <h1>📡 رصدخانه مقاومت دیجیتال</h1>
      <div class="meta-sub">موتور پرسرعت Go • آخرین به‌روزرسانی: %s</div>
    </header>

    <div class="nav-tabs">
      <button class="tab-btn active" onclick="filterTab('all', this)">همه</button>
      <button class="tab-btn" onclick="filterTab('twitter', this)">توییتر / X</button>
      <button class="tab-btn" onclick="filterTab('telegram', this)">تلگرام</button>
      <button class="tab-btn" onclick="filterTab('rss', this)">خبرگزاری‌ها</button>
    </div>

    <div class="feed-container" id="feed"></div>
  </div>

  <div class="modal" id="article-modal">
    <div class="modal-box">
      <button class="modal-close" onclick="closeModal()">✕</button>
      <div class="modal-title" id="m-title"></div>
      <div class="modal-meta" id="m-meta"></div>
      <div class="modal-body" id="m-body"></div>
    </div>
  </div>

  <script>
    const items = %s;
    let currentFilter = 'all';

    function renderFeed() {
      const container = document.getElementById('feed');
      const filtered = currentFilter === 'all' ? items : items.filter(it => it.source_type === currentFilter);
      
      if (!filtered.length) {
        container.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">موردی یافت نشد.</div>';
        return;
      }

      let html = '';
      filtered.forEach((it, idx) => {
        let badgeClass = 'badge-src';
        let typeLabel = 'X';
        if (it.source_type === 'telegram') { badgeClass = 'badge-tg'; typeLabel = 'تلگرام'; }
        else if (it.source_type === 'rss') { badgeClass = 'badge-rss'; typeLabel = 'خبر'; }

        const initial = (it.source_name_fa || it.source_name || '?').charAt(0);

        let mediaHtml = '';
        if (it.media_files && it.media_files.length) {
          mediaHtml = '<div class="media-grid">';
          it.media_files.forEach(m => {
            mediaHtml += '<img src="../' + m + '" loading="lazy" />';
          });
          mediaHtml += '</div>';
        }

        let fullArticleBtn = '';
        if (it.full_body && it.full_body.length > 250) {
          fullArticleBtn = '<button class="offline-article-btn" onclick="openArticleModal(' + idx + ')">📖 مطالعه کامل مقاله (آفلاین)</button>';
        } else if (it.article_rel_path) {
          fullArticleBtn = '<a class="offline-article-btn" href="../' + it.article_rel_path + '" target="_blank">📖 مطالعه کامل مقاله (آفلاین)</a>';
        }

        html += '<div class="tweet-card">' +
          '<div class="avatar">' + initial + '</div>' +
          '<div class="tweet-content">' +
            '<div class="tweet-header">' +
              '<span class="author-name">' + (it.source_name_fa || it.source_name) + '</span>' +
              (it.author_handle ? '<span class="author-handle">' + it.author_handle + '</span>' : '') +
              '<span class="dot">•</span>' +
              '<span class="time-badge">' + (it.published_at || '') + '</span>' +
              '<span class="' + badgeClass + '">' + typeLabel + '</span>' +
            '</div>' +
            '<div class="tweet-text" dir="' + (it.rtl ? 'rtl' : 'ltr') + '">' + escapeHtml(it.summary || it.title) + '</div>' +
            mediaHtml +
            fullArticleBtn +
          '</div>' +
        '</div>';
      });
      container.innerHTML = html;
    }

    function openArticleModal(idx) {
      const it = items[idx];
      if (!it) return;
      document.getElementById('m-title').innerText = it.title;
      document.getElementById('m-meta').innerText = 'منبع: ' + (it.source_name_fa || it.source_name) + ' | زمان: ' + it.published_at;
      
      const paragraphs = (it.full_body || it.summary).split('\n\n');
      let bodyHtml = '';
      paragraphs.forEach(p => {
        if (p.trim()) bodyHtml += '<p>' + escapeHtml(p.trim()) + '</p>';
      });
      document.getElementById('m-body').innerHTML = bodyHtml;
      document.getElementById('article-modal').classList.add('open');
    }

    function closeModal() {
      document.getElementById('article-modal').classList.remove('open');
    }

    function filterTab(type, btn) {
      currentFilter = type;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderFeed();
    }

    function escapeHtml(t) {
      if (!t) return '';
      return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    renderFeed();
  </script>
</body>
</html>`, timeStrTehran, string(jsonBytes))
}

func cleanHTML(text string) string {
	if text == "" {
		return ""
	}
	t := strings.ReplaceAll(text, "<br>", "\n")
	t = strings.ReplaceAll(t, "<br/>", "\n")
	t = strings.ReplaceAll(t, "<br />", "\n")
	t = reStripTags.ReplaceAllString(t, " ")
	t = html.UnescapeString(t)
	return strings.TrimSpace(reCleanSpaces.ReplaceAllString(t, " "))
}

func hashString(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])[:16]
}

func loadState(path string) StateData {
	var s StateData
	b, err := os.ReadFile(path)
	if err == nil {
		_ = json.Unmarshal(b, &s)
	}
	return s
}

func saveState(path string, s StateData) {
	b, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(path, b, 0644)
}

func saveMarkdownFile(path, content string) {
	_ = os.WriteFile(path, []byte(content), 0644)
}

func saveJSONFile(path string, data interface{}) {
	b, _ := json.MarshalIndent(data, "", "  ")
	_ = os.WriteFile(path, b, 0644)
}

func saveHTMLFile(path, content string) {
	_ = os.WriteFile(path, []byte(content), 0644)
}

func filterItemsByType(items []ArticleItem, t string) []ArticleItem {
	var res []ArticleItem
	for _, it := range items {
		if it.SourceType == t {
			res = append(res, it)
		}
	}
	return res
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
