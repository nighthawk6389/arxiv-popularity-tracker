---
name: post-to-reddit
description: Post trending papers from social_posts.md to Reddit using Chrome browser tools
user_invocable: true
command: post-reddit
---

# Post to Reddit

Post papers from `output/social_posts.md` to Reddit subreddits using Chrome browser automation.

## Steps

1. Read `output/social_posts.md` from the project directory
2. Parse each paper section to extract:
   - Paper title (from `**Post title:**` line)
   - Post body (from `**Post body:**` block — includes the explanation, deconstructedpapers.com link, and arxiv link)
   - Suggested subreddits (from `**Suggested subreddits:**` line, comma-separated)
3. Show the user a summary of all papers and their target subreddits
4. Get user confirmation on which papers to post and which subreddits to use
5. For each approved paper + subreddit combination:
   a. Use Chrome browser tools to navigate to `https://www.reddit.com/r/{subreddit}/submit`
   b. Wait for the page to load
   c. Find and fill in the title field with the post title
   d. Find and fill in the body/text field with the post body
   e. Take a screenshot and show the user for review before submitting
   f. Only click Submit after explicit user confirmation
   g. Wait 30 seconds between posts to avoid rate limiting

## Important

- The user MUST be logged into Reddit in the Chrome browser before starting
- ALWAYS show the user what you're about to post and get confirmation before clicking Submit
- If you can't find the title or body input fields, take a screenshot and ask the user for help
- Reddit's UI changes frequently — adapt to whatever form elements you find on the page
- Never post without explicit user approval for each individual submission

## social_posts.md Format

```markdown
## 1. Paper Title

**Suggested subreddits:** r/MachineLearning, r/artificial

**Post title:** Paper Title

**Post body:**
Explanation text.

Math-focused explanation with all equations broken down: https://www.deconstructedpapers.com/papers/...

Paper: https://arxiv.org/abs/...

**X post:**
...

---
```
