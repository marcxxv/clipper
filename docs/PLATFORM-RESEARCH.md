# Clipping economics and platform research

Checked 2026-10-22. Public sources are leads to check again before a campaign;
they do not establish a user's eligibility or likely earnings.

## Payment model

[Content Rewards campaign listings](https://contentrewards.com/c/discover) include
view-based offers. [Current creator terms](https://contentrewards.com/terms),
updated October 4, distinguish this platform from legacy Whop-hosted campaigns.
CPM means payment per 1,000 verified views; a 10% creator fee applies. Minimums,
caps, approval, available funds and tracking windows determine eligible earnings.
At a hypothetical $1/1,000 rate, 100,000 eligible paid views yield $90 after that
fee, before withdrawal fees and taxes. This is arithmetic, not an income forecast.

Measure all work time, approvals, eligible views, settled earnings and actual
withdrawals. A dashboard estimate or a viral clip alone does not validate a
business. Check the user's country and withdrawal method before investing time.

[OpusClip](https://www.opus.pro/pricing) lists Starter at $15/month. Low-cost
automatic captions and clipping are widely available; editorial quality,
audience fit and reliable delivery need separate validation. A fair comparison
uses the same permitted source, clip requirements and human review rubric.

[YouTube](https://support.google.com/youtube/answer/1311392) separates reused
content monetization from copyright permission. Campaign compensation is a
different revenue source from platform advertising. Do not assume captions or
permission alone qualify a repost for ad revenue.

## What X source can teach us

Reviewed [xai-org/x-algorithm at 989fb912](https://github.com/xai-org/x-algorithm/tree/989fb91254d461bf4b9df53fb12d5c9a61c2b354),
including its README, `home-mixer/scorers/value_model.rs` and `phoenix/README.md`.
This is a newer source than the older `twitter/the-algorithm` publication.

X combines viewer-specific predicted actions and attention values, including
watching/dwell, shares and negative feedback. Ranking also considers diversity
and filtering. Published weights multiply predicted probabilities or continuous
values, not raw engagement counts: a report does not simply cancel a fixed
number of likes. The repository omits some prompts/rules; published code does
not supply Clipper with real viewer histories or a trained, calibrated predictor
for its audience. Public source inspection is sufficient; no binary reverse
engineering is needed.

Useful hypotheses: a clear audience, a satisfying payoff, watch retention and
share-worthy substance may matter beyond a loud opening. These are hypotheses
to test on permitted posts, not new automatic scoring rules. X's ranking cannot
be assumed to describe TikTok, Reels or Shorts. Do not transplant X weights into
the current hook score or present that score as a probability of going viral.

Next improvement should be an optional local outcome log: source/clip, platform,
campaign, hook variant, human time, available retention/share metrics, approval
and settled earnings. Compare similar clips within one niche and platform;
account age, posting time and topic can confound results. Only change selection
weights after enough comparable outcomes support it. No automatic posting or
paid analytics integration is implied.
