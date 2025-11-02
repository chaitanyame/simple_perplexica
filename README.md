# Simple Perplexica 🔍# Perplexica 🔍



**A high-performance, cost-optimized AI search API with intelligent web search capabilities.**[![GitHub Repo stars](https://img.shields.io/github/stars/ItzCrazyKns/Perplexica?style=social)](https://github.com/ItzCrazyKns/Perplexica/stargazers)

[![GitHub forks](https://img.shields.io/github/forks/ItzCrazyKns/Perplexica?style=social)](https://github.com/ItzCrazyKns/Perplexica/network/members)

Built with Python, FastAPI, PydanticAI, and OpenRouter - delivering smart, cited answers while keeping costs minimal through advanced caching and optimization strategies.[![GitHub watchers](https://img.shields.io/github/watchers/ItzCrazyKns/Perplexica?style=social)](https://github.com/ItzCrazyKns/Perplexica/watchers)

[![Docker Pulls](https://img.shields.io/docker/pulls/itzcrazykns1337/perplexica?color=blue)](https://hub.docker.com/r/itzcrazykns1337/perplexica)

---[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/ItzCrazyKns/Perplexica/blob/master/LICENSE)

[![GitHub last commit](https://img.shields.io/github/last-commit/ItzCrazyKns/Perplexica?color=green)](https://github.com/ItzCrazyKns/Perplexica/commits/master)

## ✨ Features[![Discord](https://dcbadge.limes.pink/api/server/26aArMy8tT?style=flat)](https://discord.gg/26aArMy8tT)



🚀 **High Performance**Perplexica is a **privacy-focused AI answering engine** that runs entirely on your own hardware. It combines knowledge from the vast internet with support for **local LLMs** (Ollama) and cloud providers (OpenAI, Claude, Groq), delivering accurate answers with **cited sources** while keeping your searches completely private.

- Redis caching for 75% cost reduction ($730/year → $182/year)

- Async URL fetching for 3x faster processing![preview](.assets/perplexica-screenshot.png)

- HTTP connection pooling for 30-50% faster API calls

- Sub-6 second response times for complex queriesWant to know more about its architecture and how it works? You can read it [here](https://github.com/ItzCrazyKns/Perplexica/tree/master/docs/architecture/README.md).



🎯 **Intelligent Search**## ✨ Features

- **Focus Modes**: Web search, academic papers, YouTube videos, Reddit discussions, Wolfram Alpha calculations, writing assistance

- **Quality Mode**: Fetches and analyzes full URL content (not just snippets)🤖 **Support for all major AI providers** - Use local LLMs through Ollama or connect to OpenAI, Anthropic Claude, Google Gemini, Groq, and more. Mix and match models based on your needs.

- **Temporal Understanding**: SpaCy-powered detection of time-based queries (recent, today, this week, etc.)

- **Smart Ranking**: Cosine similarity reranking for most relevant results⚡ **Smart search modes** - Choose Balanced Mode for everyday searches, Fast Mode when you need quick answers, or wait for Quality Mode (coming soon) for deep research.



💰 **Cost Optimized**🎯 **Six specialized focus modes** - Get better results with modes designed for specific tasks: Academic papers, YouTube videos, Reddit discussions, Wolfram Alpha calculations, writing assistance, or general web search.

- Free-tier LLM usage (DeepSeek via OpenRouter)

- Intelligent caching with configurable TTLs🔍 **Web search powered by SearxNG** - Access multiple search engines while keeping your identity private. Support for Tavily and Exa coming soon for even better results.

- Efficient embedding reuse

- ~$15/month for moderate usage with caching📷 **Image and video search** - Find visual content alongside text results. Search isn't limited to just articles anymore.



🔍 **Search Features**📄 **File uploads** - Upload documents and ask questions about them. PDFs, text files, images - Perplexica understands them all.

- SearxNG integration for privacy-focused web search

- SerperDev API support for enhanced results🌐 **Search specific domains** - Limit your search to specific websites when you know where to look. Perfect for technical documentation or research papers.

- URL content fetching and parsing (HTML + PDF)

- Image and video search capabilities💡 **Smart suggestions** - Get intelligent search suggestions as you type, helping you formulate better queries.



📊 **Production Ready**📚 **Discover** - Browse interesting articles and trending content throughout the day. Stay informed without even searching.

- Comprehensive error handling and logging

- Rate limiting and CORS support🕒 **Search history** - Every search is saved locally so you can revisit your discoveries anytime. Your research is never lost.

- Health check endpoints

- Docker-based deployment✨ **More coming soon** - We're actively developing new features based on community feedback. Join our Discord to help shape Perplexica's future!

- Persistent conversation storage with mem0

## Sponsors

---

Perplexica's development is powered by the generous support of our sponsors. Their contributions help keep this project free, open-source, and accessible to everyone.

## 🏗️ Architecture

<div align="center">

```  

┌─────────────┐  

│   Client    │<a href="https://www.warp.dev/perplexica">

└──────┬──────┘  <img alt="Warp Terminal" src=".assets/sponsers/warp.png" width="100%">

       │</a>

       ▼

┌─────────────────────────────────────┐**[Warp](https://www.warp.dev/perplexica)** - The AI-powered terminal revolutionizing development workflows

│   FastAPI Server (Port 3000)        │

│   ┌──────────────────────────────┐  │</div>

│   │  Search Endpoint             │  │

│   │  • Focus mode routing        │  │## Installation

│   │  • Temporal detection        │  │

│   │  • Quality mode processing   │  │There are mainly 2 ways of installing Perplexica - With Docker, Without Docker. Using Docker is highly recommended.

│   └──────────────────────────────┘  │

│   ┌──────────────────────────────┐  │### Getting Started with Docker (Recommended)

│   │  Redis Cache Layer           │  │

│   │  • Embedding cache (7d TTL)  │  │Perplexica can be easily run using Docker. Simply run the following command:

│   │  • Response cache (1d TTL)   │  │

│   │  • 4.6x faster cached queries│  │```bash

│   └──────────────────────────────┘  │docker run -d -p 3000:3000 -v perplexica-data:/home/perplexica/data -v perplexica-uploads:/home/perplexica/uploads --name perplexica itzcrazykns1337/perplexica:latest

│   ┌──────────────────────────────┐  │```

│   │  OpenRouter Integration      │  │

│   │  • PydanticAI agents         │  │This will pull and start the Perplexica container with the bundled SearxNG search engine. Once running, open your browser and navigate to http://localhost:3000. You can then configure your settings (API keys, models, etc.) directly in the setup screen.

│   │  • Async embeddings          │  │

│   │  • Connection pooling        │  │**Note**: The image includes both Perplexica and SearxNG, so no additional setup is required. The `-v` flags create persistent volumes for your data and uploaded files.

│   └──────────────────────────────┘  │

└─────────────────────────────────────┘#### Using Perplexica with Your Own SearxNG Instance

       │               │

       ▼               ▼If you already have SearxNG running, you can use the slim version of Perplexica:

┌─────────────┐ ┌─────────────┐

│  SearxNG    │ │   Redis     │```bash

│  Port 8080  │ │  Port 6379  │docker run -d -p 3000:3000 -e SEARXNG_API_URL=http://your-searxng-url:8080 -v perplexica-data:/home/perplexica/data -v perplexica-uploads:/home/perplexica/uploads --name perplexica itzcrazykns1337/perplexica:slim-latest

└─────────────┘ └─────────────┘```

```

**Important**: Make sure your SearxNG instance has:

**Performance Metrics:**

- First query (cold): ~5s- JSON format enabled in the settings

- Cached query: ~1s (4.6x faster)- Wolfram Alpha search engine enabled

- Quality mode: <6s with URL enrichment

- URL fetching: 3x faster with async processingReplace `http://your-searxng-url:8080` with your actual SearxNG URL. Then configure your AI provider settings in the setup screen at http://localhost:3000.



---#### Advanced Setup (Building from Source)



## 🚀 Quick StartIf you prefer to build from source or need more control:



### Prerequisites1. Ensure Docker is installed and running on your system.

- Docker and Docker Compose2. Clone the Perplexica repository:

- OpenRouter API key (free tier available)

- (Optional) SerperDev API key   ```bash

   git clone https://github.com/ItzCrazyKns/Perplexica.git

### Installation   ```



1. **Clone the repository**3. After cloning, navigate to the directory containing the project files.

```bash

git clone https://github.com/chaitanyame/simple_perplexica.git4. Build and run using Docker:

cd simple_perplexica

```   ```bash

   docker build -t perplexica .

2. **Set up environment variables**   docker run -d -p 3000:3000 -v perplexica-data:/home/perplexica/data -v perplexica-uploads:/home/perplexica/uploads --name perplexica perplexica

```bash   ```

cp .env.example .env

# Edit .env and add your OpenRouter API key5. Access Perplexica at http://localhost:3000 and configure your settings in the setup screen.

```

**Note**: After the containers are built, you can start Perplexica directly from Docker without having to open a terminal.

Required environment variables:

```env### Non-Docker Installation

OPENROUTER_API_KEY=your_key_here

OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free1. Install SearXNG and allow `JSON` format in the SearXNG settings. Make sure Wolfram Alpha search engine is also enabled.

SERPERDEV_API_KEY=your_key_here  # Optional but recommended2. Clone the repository:

```

   ```bash

3. **Start the services**   git clone https://github.com/ItzCrazyKns/Perplexica.git

```bash   cd Perplexica

docker compose up -d   ```

```

3. Install dependencies:

This will start:

- **API Server** (port 3000) - Main search API   ```bash

- **SearxNG** (port 8080) - Privacy-focused search engine   npm i

- **Redis** (port 6379) - Cache layer for performance   ```

- **UI** (port 8501) - Optional Streamlit testing interface

4. Build the application:

4. **Verify it's working**

```bash   ```bash

curl http://localhost:3000/health   npm run build

```   ```



---5. Start the application:



## 📖 API Usage   ```bash

   npm run start

### Basic Search Request   ```



```bash6. Open your browser and navigate to http://localhost:3000 to complete the setup and configure your settings (API keys, models, SearxNG URL, etc.) in the setup screen.

curl -X POST http://localhost:3000/api/search \

  -H "Content-Type: application/json" \**Note**: Using Docker is recommended as it simplifies the setup process, especially for managing environment variables and dependencies.

  -d '{

    "query": "What are the latest developments in AI?",See the [installation documentation](https://github.com/ItzCrazyKns/Perplexica/tree/master/docs/installation) for more information like updating, etc.

    "focusMode": "webSearch",

    "optimizationMode": "balanced"### Troubleshooting

  }'

```#### Local OpenAI-API-Compliant Servers



### Quality Mode (URL Enrichment)If Perplexica tells you that you haven't configured any chat model providers, ensure that:



```bash1. Your server is running on `0.0.0.0` (not `127.0.0.1`) and on the same port you put in the API URL.

curl -X POST http://localhost:3000/api/search \2. You have specified the correct model name loaded by your local LLM server.

  -H "Content-Type: application/json" \3. You have specified the correct API key, or if one is not defined, you have put _something_ in the API key field and not left it empty.

  -d '{

    "query": "Explain quantum computing",#### Ollama Connection Errors

    "focusMode": "webSearch",

    "optimizationMode": "quality"If you're encountering an Ollama connection error, it is likely due to the backend being unable to connect to Ollama's API. To fix this issue you can:

  }'

```1. **Check your Ollama API URL:** Ensure that the API URL is correctly set in the settings menu.

2. **Update API URL Based on OS:**

### Response Format

   - **Windows:** Use `http://host.docker.internal:11434`

```json   - **Mac:** Use `http://host.docker.internal:11434`

{   - **Linux:** Use `http://<private_ip_of_host>:11434`

  "answer": "Detailed answer with citations...",

  "sources": [   Adjust the port number if you're using a different one.

    {

      "title": "Article Title",3. **Linux Users - Expose Ollama to Network:**

      "url": "https://example.com/article",

      "content": "Snippet or full content..."   - Inside `/etc/systemd/system/ollama.service`, you need to add `Environment="OLLAMA_HOST=0.0.0.0:11434"`. (Change the port number if you are using a different one.) Then reload the systemd manager configuration with `systemctl daemon-reload`, and restart Ollama by `systemctl restart ollama`. For more information see [Ollama docs](https://github.com/ollama/ollama/blob/main/docs/faq.md#setting-environment-variables-on-linux)

    }

  ]   - Ensure that the port (default is 11434) is not blocked by your firewall.

}

```#### Lemonade Connection Errors



### Focus ModesIf you're encountering a Lemonade connection error, it is likely due to the backend being unable to connect to Lemonade's API. To fix this issue you can:



- `webSearch` - General web search1. **Check your Lemonade API URL:** Ensure that the API URL is correctly set in the settings menu.

- `academicSearch` - Academic papers and research2. **Update API URL Based on OS:**

- `youtubeSearch` - YouTube videos

- `redditSearch` - Reddit discussions   - **Windows:** Use `http://host.docker.internal:8000`

- `wolframAlphaSearch` - Computational queries   - **Mac:** Use `http://host.docker.internal:8000`

- `writingAssistant` - Writing help   - **Linux:** Use `http://<private_ip_of_host>:8000`



### Optimization Modes   Adjust the port number if you're using a different one.



- `speed` - Fast responses, basic results3. **Ensure Lemonade Server is Running:**

- `balanced` - Balance between speed and quality (default)

- `quality` - Fetch full URL content for comprehensive answers   - Make sure your Lemonade server is running and accessible on the configured port (default is 8000).

   - Verify that Lemonade is configured to accept connections from all interfaces (`0.0.0.0`), not just localhost (`127.0.0.1`).

---   - Ensure that the port (default is 8000) is not blocked by your firewall.



## 🧪 Testing## Using as a Search Engine



Run the comprehensive test suite:If you wish to use Perplexica as an alternative to traditional search engines like Google or Bing, or if you want to add a shortcut for quick access from your browser's search bar, follow these steps:



```powershell1. Open your browser's settings.

# Test all optimizations2. Navigate to the 'Search Engines' section.

.\test_optimizations.ps13. Add a new site search with the following URL: `http://localhost:3000/?q=%s`. Replace `localhost` with your IP address or domain name, and `3000` with the port number if Perplexica is not hosted locally.

4. Click the add button. Now, you can use Perplexica directly from your browser's search bar.

# Test quality mode with various scenarios

.\test_quality_mode_scenarios.ps1## Using Perplexica's API



# Test critical fixes (CORS, logging, rate limiting)Perplexica also provides an API for developers looking to integrate its powerful search engine into their own applications. You can run searches, use multiple models and get answers to your queries.

.\test_critical_fixes.ps1

```For more details, check out the full documentation [here](https://github.com/ItzCrazyKns/Perplexica/tree/master/docs/API/SEARCH.md).



---## Expose Perplexica to network



## 🎛️ ConfigurationPerplexica runs on Next.js and handles all API requests. It works right away on the same network and stays accessible even with port forwarding.



### Environment Variables## One-Click Deployment



```env[![Deploy to Sealos](https://raw.githubusercontent.com/labring-actions/templates/main/Deploy-on-Sealos.svg)](https://usw.sealos.io/?openapp=system-template%3FtemplateName%3Dperplexica)

# Required[![Deploy to RepoCloud](https://d16t0pc4846x52.cloudfront.net/deploylobe.svg)](https://repocloud.io/details/?app_id=267)

OPENROUTER_API_KEY=sk-or-...[![Run on ClawCloud](https://raw.githubusercontent.com/ClawCloud/Run-Template/refs/heads/main/Run-on-ClawCloud.svg)](https://template.run.claw.cloud/?referralCode=U11MRQ8U9RM4&openapp=system-fastdeploy%3FtemplateName%3Dperplexica)

OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free[![Deploy on Hostinger](https://assets.hostinger.com/vps/deploy.svg)](https://www.hostinger.com/vps/docker-hosting?compose_url=https://raw.githubusercontent.com/ItzCrazyKns/Perplexica/refs/heads/master/docker-compose.yaml)



# Optional## Upcoming Features

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

OPENROUTER_EMBEDDING_MODEL=text-embedding-3-small- [x] Add settings page

SEARXNG_URL=http://searxng:8080- [x] Adding support for local LLMs

SERPERDEV_API_KEY=your_key_here- [x] History Saving features

- [x] Introducing various Focus Modes

# Performance- [x] Adding API support

REDIS_URL=redis://redis:6379- [x] Adding Discover

REDIS_ENABLED=true- [ ] Finalizing Copilot Mode

MEM0_ENABLED=false

## Support Us

# Server

PORT=3001If you find Perplexica useful, consider giving us a star on GitHub. This helps more people discover Perplexica and supports the development of new features. Your support is greatly appreciated.

HOST=0.0.0.0

```### Donations



### Docker Compose PortsWe also accept donations to help sustain our project. If you would like to contribute, you can use the following options to donate. Thank you for your support!



- `3000` - Main API server| Ethereum                                              |

- `8080` - SearxNG search engine| ----------------------------------------------------- |

- `6379` - Redis cache| Address: `0xB025a84b2F269570Eb8D4b05DEdaA41D8525B6DD` |

- `8501` - Streamlit UI (optional)

## Contribution

---

Perplexica is built on the idea that AI and large language models should be easy for everyone to use. If you find bugs or have ideas, please share them in via GitHub Issues. For more information on contributing to Perplexica you can read the [CONTRIBUTING.md](CONTRIBUTING.md) file to learn more about Perplexica and how you can contribute to it.

## 📊 Performance Optimizations

## Help and Support

The MVP includes 4 major performance optimizations:

If you have any questions or feedback, please feel free to reach out to us. You can create an issue on GitHub or join our Discord server. There, you can connect with other users, share your experiences and reviews, and receive more personalized help. [Click here](https://discord.gg/EFwsmQDgAu) to join the Discord server. To discuss matters outside of regular support, feel free to contact me on Discord at `itzcrazykns`.

### 1. Redis Caching (75% cost reduction)

- **Embedding cache**: 7-day TTLThank you for exploring Perplexica, the AI-powered search engine designed to enhance your search experience. We are constantly working to improve Perplexica and expand its capabilities. We value your feedback and contributions which help us make Perplexica even better. Don't forget to check back for updates and new features!

- **Response cache**: 1-day TTL
- **Result**: Identical queries 4.6x faster (5s → 1s)
- **Savings**: $730/year → $182/year

### 2. Async URL Fetching (3x faster)
- Concurrent processing with `asyncio.gather()`
- **Before**: 9+ seconds for 3 URLs
- **After**: ~3 seconds (3x faster)

### 3. HTTP Connection Pooling (30-50% faster)
- Singleton `httpx.AsyncClient`
- 100 max connections, 20 keep-alive
- Connection reuse across all API calls

### 4. mem0 Conversation Storage
- Persistent conversation history
- Session-based tracking
- Survives container restarts

See [OPTIMIZATIONS_SUMMARY.md](OPTIMIZATIONS_SUMMARY.md) for detailed performance metrics.

---

## 🗂️ Project Structure

```
simple_perplexica/
├── services/
│   └── searchsvc/            # Main API service
│       ├── app/
│       │   ├── main.py       # FastAPI application
│       │   ├── models.py     # Pydantic models
│       │   ├── providers/
│       │   │   └── openrouter.py  # OpenRouter integration
│       │   ├── search_clients/
│       │   │   ├── searxng.py     # SearxNG client
│       │   │   └── serperdev.py   # SerperDev client
│       │   └── utils/
│       │       ├── cache.py       # Redis caching
│       │       ├── fetch_urls.py  # URL content fetching
│       │       ├── http_client.py # Connection pooling
│       │       └── memory.py      # mem0 integration
│       ├── Dockerfile
│       └── requirements.txt
├── searxng/                  # SearxNG configuration
├── docker-compose.yaml       # Service orchestration
└── test_*.ps1               # Test scripts
```

---

## 🔧 Development

### Running Locally (Without Docker)

```bash
cd services/searchsvc

# Install dependencies
pip install -r requirements.txt

# Download SpaCy model
python -m spacy download en_core_web_sm

# Set environment variables
export OPENROUTER_API_KEY=your_key_here
export SEARXNG_URL=http://localhost:8080
export REDIS_URL=redis://localhost:6379

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api

# Search for specific patterns
docker compose logs api | grep -i "cache\|error"
```

### Rebuilding After Changes

```bash
docker compose build api
docker compose up -d api
```

---

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:3000/health
```

### Cache Statistics
```bash
curl http://localhost:3000/api/cache/stats
```

### Container Status
```bash
docker compose ps
```

---

## 🐛 Troubleshooting

### API returns empty responses
- Check OpenRouter API key is set correctly
- Verify SerperDev API key is valid (or disable it)
- Check logs: `docker compose logs api`

### Cache not working
- Verify Redis is running: `docker compose ps redis`
- Check Redis connection: `docker exec simple_perplexica-redis-1 redis-cli PING`
- Review cache logs: `docker compose logs api | grep cache`

### Slow responses
- Check if caching is enabled (`REDIS_ENABLED=true`)
- Verify async URL fetching is working (logs should show "Concurrent URL fetching")
- Monitor Redis: `docker stats simple_perplexica-redis-1`

### SearxNG errors
- Ensure SearxNG is running: `curl http://localhost:8080`
- Check SearxNG logs: `docker compose logs searxng`
- Verify configuration in `searxng/settings.yml`

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built upon concepts from [Perplexica](https://github.com/ItzCrazyKns/Perplexica)
- Uses [SearxNG](https://github.com/searxng/searxng) for privacy-focused search
- Powered by [OpenRouter](https://openrouter.ai/) for affordable LLM access
- Enhanced with [PydanticAI](https://ai.pydantic.dev/) for type-safe AI agents

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/chaitanyame/simple_perplexica/issues)
- **Documentation**: See the `docs/` folder
- **Tests**: Run `test_*.ps1` scripts for examples

---

**Made with ❤️ for the AI search community**
