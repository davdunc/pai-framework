# Analyst Sources

Sources for trading intelligence extraction. Add YouTube channels, podcasts, blogs, and analysts here. The IngestContent workflow uses this to tag and classify extracted content.

## How to Add a Source

```
User: "ingest this video https://youtube.com/watch?v=xyz"
```

The system will:
1. Extract the transcript
2. Identify the source/channel
3. Run setup, regime, and psychology extraction patterns
4. Append insights to the intelligence base
5. Store full extract in `Intelligence/Analysts/[SourceName].md`

## Active Sources

*Add sources as you discover them. Format:*

### [SourceName]
- **Platform:** YouTube / Podcast / Blog
- **URL:** [channel/feed URL]
- **Focus:** [What they specialize in]
- **Key value:** [Why you follow them]

---

*No sources configured yet. Run `/Trading ingest` with a YouTube URL to start building the intelligence base. Sources will be auto-catalogued here.*
