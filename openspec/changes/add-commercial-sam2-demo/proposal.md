# Proposal: Add Commercial SAM2 Interactive Demo

## Summary

Add a modern, interactive SAM2 segmentation demo module to the commercial frontend for quick product demonstration purposes. This feature will showcase AI-powered image segmentation with intelligent labeling suggestions powered by LLMs.

## Problem Statement

Currently, the SAM2 interactive segmentation functionality exists only in the CTAI L3 Mask Annotation interface (Vue.js), which:

1. Is deeply integrated with patient data workflows
2. Requires full CTAI authentication and setup
3. Is not accessible for quick demonstrations or marketing purposes
4. Does not leverage LLM capabilities for intelligent label suggestions

The commercial frontend (React) needs a standalone, visually appealing demo module that:

- Provides instant value to users without requiring complex DICOM uploads
- Demonstrates the AI segmentation capabilities in a modern UI
- Offers intelligent label suggestions powered by LLMs
- Aligns with the commercial frontend's design system

## Goals

1. **Quick Demo Experience**: Enable users to quickly experience SAM2 segmentation with simple image uploads (PNG/JPG)
2. **Modern UI/UX**: Create a visually appealing, responsive interface that matches the commercial frontend's design standards
3. **LLM Integration**: Integrate third-party LLM (OpenAI/Claude) to provide intelligent label suggestions based on segmented regions
4. **Marketing Value**: Provide a compelling product showcase that can attract potential subscribers
5. **Code Reusability**: Leverage existing SAM2 service infrastructure while adapting for general-purpose images

## Non-Goals

1. Replace or modify the existing L3 Mask Editor in CTAI
2. Support DICOM format in this initial implementation
3. Save segmentation results to patient records
4. Provide full medical annotation features (measurements, reports, etc.)

## Scope

### In Scope

- Dashboard card module for demo access
- Image upload interface (PNG/JPG only)
- SAM2 interactive click segmentation (foreground/background points)
- Text label input for each segmented region
- LLM-powered label suggestions (client-side API calls)
- Modern, bordered, rounded UI design matching commercial frontend
- Leader line labels pointing to segmented regions (outside image bounds)
- Result visualization and export

### Out of Scope

- DICOM image support
- Integration with patient management system
- Medical-grade reporting
- Annotation history/versioning
- Multi-user collaboration

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Commercial Frontend (React)                    │
│  ┌────────────────────────────────────────────┐ │
│  │  DashboardPage                             │ │
│  │    ↓                                       │ │
│  │  DemoImageSegmentation Component           │ │
│  │    │                                       │ │
│  │    ├─→ Image Upload (PNG/JPG)             │ │
│  │    ├─→ Canvas Layer (Click Points)        │ │
│  │    ├─→ Label Input with LLM Suggestions   │ │
│  │    └─→ Result Display                     │ │
│  └────────────────────────────────────────────┘ │
│           ↓                    ↓                 │
│     SAM2 Service        LLM API (Client-side)   │
│     (via Nginx)         (OpenAI/Anthropic)      │
└─────────────────────────────────────────────────┘
```

### Key Components

1. **DemoSegmentationCard** (Dashboard entry point)
   - Visual card with CTA
   - Expands to full demo interface or opens modal

2. **ImageSegmentationDemo** (Main component)
   - Image upload area
   - SAM2 interactive canvas
   - Label input with LLM suggestions
   - Results panel

3. **SAM2Canvas** (Reusable canvas component)
   - Click point collection
   - Mask visualization
   - Leader line rendering

4. **LabelSuggestionService** (New service)
   - Client-side LLM API integration
   - Image + segmentation context to LLM
   - Parse and display suggestions

### UI Design Principles

- **Modern aesthetics**: Rounded corners (border-radius: 12px+), soft shadows
- **Bordered containers**: Clear visual boundaries for each section
- **Leader line labels**: Text labels positioned outside image with connecting lines
- **Consistent styling**: Match shadcn/ui component library
- **Responsive layout**: Grid/flex layouts that work on different screen sizes
- **Visual feedback**: Loading states, hover effects, smooth transitions

## Dependencies

- Existing SAM2 service (Docker container on port 8000)
- Commercial frontend build system (React + TypeScript + Vite)
- shadcn/ui component library
- Canvas API for rendering
- LLM API keys (OpenAI or Anthropic) - configured via environment variables

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| SAM2 service latency | Medium | Show clear loading indicators; cache results |
| LLM API costs | Medium | Rate limiting; use cheaper models; cache suggestions |
| Image format compatibility | Low | Validate formats client-side; provide clear error messages |
| Canvas rendering performance | Low | Optimize redraw logic; throttle mouse events |
| Cross-origin issues with SAM2 | Medium | Ensure Nginx CORS configuration is correct |

## Success Metrics

1. Demo module accessible within 2 clicks from dashboard
2. Image segmentation completes in < 5 seconds for typical images
3. LLM suggestions returned in < 3 seconds
4. UI passes visual design review (rounded corners, proper borders, modern feel)
5. Feature works across modern browsers (Chrome, Firefox, Safari)

## Alternatives Considered

### Alternative 1: Full Standalone Page
- **Pros**: More screen space, cleaner routing
- **Cons**: Requires navigation away from dashboard; less integrated feel
- **Decision**: Rejected in favor of dashboard card for better UX

### Alternative 2: Backend LLM Integration
- **Pros**: Centralized API key management, easier rate limiting
- **Cons**: Additional backend development; slower iteration
- **Decision**: Rejected for MVP; can be implemented later if needed

### Alternative 3: Port L3MaskEditor Directly
- **Pros**: Faster initial development
- **Cons**: Vue-React incompatibility; medical-specific UI not suitable
- **Decision**: Rejected; build React-native component instead

## Timeline Estimate

- **Proposal & Design**: 1 day
- **UI Component Development**: 2-3 days
- **SAM2 Integration**: 1 day
- **LLM Integration**: 1-2 days
- **Testing & Polish**: 1 day
- **Total**: 6-8 days

## Stakeholders

- **Product Team**: Needs compelling demo for marketing
- **Engineering Team**: Maintains commercial frontend
- **End Users**: Experience simplified SAM2 capabilities

## Approval Required

- [ ] Product Owner: Confirms feature aligns with product roadmap
- [ ] Technical Lead: Approves architectural approach
- [ ] Design Lead: Reviews UI mockups and design system compliance

## Related Changes

- None (this is a new feature addition)

## References

- Existing L3MaskEditor implementation: `CTAI_web/src/components/L3MaskEditor.vue`
- SAM2 integration guide: `docs/SAM2/SAM2_DEPLOYMENT.md`
- Commercial frontend architecture: `commercial/frontend/DEVELOPMENT_GUIDE.md`
- OpenSpec specs: `openspec/specs/image-segmentation/spec.md`
