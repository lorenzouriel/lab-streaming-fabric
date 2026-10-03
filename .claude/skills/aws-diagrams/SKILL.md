---
name: aws-diagrams
description: Always use when user asks to create, generate, or build an AWS architecture diagram, cloud infrastructure diagram, or system diagram with AWS services. Also activates for draw.io diagrams mentioning AWS services like Lambda, DynamoDB, S3, API Gateway, MSK, ECS, etc.
---

# AWS Architecture Diagram Skill

Generate AWS architecture diagrams as native `.drawio` files using the official AWS Architecture Icons (draw.io's built-in `mxgraph.aws4` stencil library). Optionally export to PNG, SVG, or PDF with embedded XML, so exported files stay editable in draw.io.

## How to create a diagram

1. **Pick a starting point** — `templates/` has five ready-made diagrams (see [templates/README.md](templates/README.md)); copy the closest one instead of starting from an empty canvas when it fits.
2. **Look up every icon** in `references/` (index below) — never guess a stencil name.
3. **Generate draw.io XML** in mxGraphModel format following the rules below.
4. **Write the XML** to a `.drawio` file with the Write tool.
5. **Export to PNG and review it** (see Export + Two-Step Edit) — broken stencils are invisible in raw XML.
6. **If the user asked for an export format** (png/svg/pdf), leave that file next to the `.drawio`; otherwise print the path.

## Icon reference files (load by category, on demand)

| File | Covers |
|------|--------|
| `references/aws-icons-common.md` | Groups, general resources, edge styles, base mxfile template, the two icon patterns |
| `references/aws-icons-compute.md` | Lambda, EC2, ECS, EKS, Fargate, Batch |
| `references/aws-icons-database.md` | DynamoDB, RDS, Aurora, ElastiCache, Redshift |
| `references/aws-icons-integration.md` | API Gateway, SQS, SNS, EventBridge, Step Functions, AppSync |
| `references/aws-icons-networking.md` | CloudFront, Route 53, VPC, ELB, Direct Connect |
| `references/aws-icons-storage.md` | S3, EFS, EBS, Glacier, Backup |
| `references/aws-icons-security.md` | IAM, Cognito, KMS, WAF, Shield, Secrets Manager |
| `references/aws-icons-analytics-ml.md` | Kinesis, MSK, Athena, Glue, Bedrock, SageMaker |
| `references/aws-icons-iot-migration-devtools.md` | IoT Core, DMS, CodePipeline, CodeBuild, CloudFormation |
| `references/aws-icons-3d.md` | Legacy `mxgraph.aws3d` isometric library (3D mode only) |
| `references/aws-icons-allied-telesis.md` | Generic isometric hardware (clients, racks, switches) for 3D mode |

**Always verify icon names against these files. An empty colored box means the stencil name is wrong.**

## Layout Rules

- **Left-to-right flow** for data/request path
- **UI/Frontend on the LEFT** (users access from left side)
- **Data sources / external systems on the RIGHT**
- Use horizontal lanes for parallel paths (top lane, bottom lane)
- **Minimum 220px horizontal spacing** between icons (room for edge labels)
- **Minimum 250px vertical spacing** between lanes
- Secondary/auxiliary services (monitoring, DLQ) go BELOW main flow with 280px+ gap
- Canvas: `pageWidth="2400" pageHeight="1400"`, viewport `dx="2800" dy="1600"`
- Always include a title block after the background rectangle:
```xml
<mxCell value="&lt;b&gt;Diagram Title&lt;/b&gt;&lt;br&gt;Author | Date | Version" style="text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;rounded=0;fontSize=14;spacing=8;" vertex="1" parent="1">
  <mxGeometry x="40" y="30" width="420" height="60" as="geometry" />
</mxCell>
```

## Icon Style

- Icon size: **78x78px** for main services, **65x65px** for secondary
- Use `sketch=0` on all icons
- Font size: **12px** for labels
- **NO colored backgrounds** on group boxes — always `fillColor=none`

### Two icon patterns — CRITICAL

| Pattern | Style | strokeColor | Size |
|---------|-------|-------------|------|
| Service-level (framed) | `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<name>` | **`#ffffff`** (without it the white glyph disappears) | 78x78 |
| Resource-level (standalone) | `shape=mxgraph.aws4.<name>` | **`none`** (`#ffffff` breaks these) | 78x78 or 48x48 |

**Confusing these two guarantees broken icons.**

### 3D / Isometric Diagrams — different icon library
If the user asks for a **3D**, **isometric**, or "AWS 3D" diagram, do NOT fake it by placing flat `aws4` icons on hand-built platform/pedestal shapes. draw.io has a real, separate built-in library: `mxgraph.aws3d.*`.
- Load `references/aws-icons-3d.md` before picking any icon — verified shape table, style prefix, sizes, native `isometricEdgeStyle` edge templates.
- Legacy pre-2019 set with **much smaller coverage** than `aws4` (no API Gateway, ECS/EKS/Fargate, Step Functions, EventBridge, SNS, Aurora, CloudWatch, IAM). Check the gap table there before assuming an icon exists; flag substitutions to the user rather than guessing a stencil name.
- Shape names are camelCase (`dynamoDb`, not `dynamodb`).
- Generic hardware (clients, on-prem servers, racks, switches) with no AWS icon: `references/aws-icons-allied-telesis.md`.
- These icons are already 3D — arrange them in an ascending isometric staircase (diagonal offsets), don't add fake platforms underneath.
- Use `edgeStyle=isometricEdgeStyle` (with `endArrow=block` override for reliable arrowheads) instead of `orthogonalEdgeStyle`.

## Edge Style — CRITICAL FOR CLEAN DIAGRAMS

**Base edge style:**
```
edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;
```

**Edge label rules:**
- Keep labels SHORT (1-2 words max). Detail goes in icon labels, not edge labels.
- Always add `labelBackgroundColor=#F5F5F5;fontSize=11;` to edges with labels
- Horizontal edges: push the label above the line with `verticalAlign=bottom;`; vertical edges: to the left with `align=right;`
- For edges WITHOUT labels: omit `value` entirely (not `value=""`)
- When NOT to label: if the flow is obvious (Lambda → DynamoDB doesn't need "Write")

**For edges to services ABOVE or BELOW main flow, use explicit exit/entry points:**
- Exit bottom: `exitX=0.5;exitY=1;exitDx=0;exitDy=0;` / Enter top: `entryX=0.5;entryY=0;entryDx=0;entryDy=0;`
- Exit top: `exitX=0.5;exitY=0;exitDx=0;exitDy=0;` / Enter bottom: `entryX=0.5;entryY=1;entryDx=0;entryDy=0;`
- This prevents draw.io from routing lines through other icons

**Edge types:**
- Solid (`strokeWidth=2`): primary data flow
- Dashed (`strokeWidth=2;dashed=1;`): optional/async
- Red dashed (`strokeWidth=2;dashed=1;strokeColor=#DD344C;`): error path

**Edge attachment (CRITICAL — fixes "green cross" problem):**
- Every edge MUST have both `source="<cell-id>"` and `target="<cell-id>"` referencing valid cell IDs
- NEVER create floating/unattached edges
- Always include `exitX/exitY` and `entryX/entryY` to fix the connection points on the shape perimeter
- **Cross-container edges:** when source and target sit in different containers, set the edge's `parent="1"`

## Visual Quality: straight arrows, no overlaps, professional layout

A diagram with correct icons but a messy layout still reads as unprofessional. Check every diagram against these concrete, checkable rules before finishing:

- **Align nodes to a consistent axis so edges are single, straight segments.** Keep the horizontal or vertical delta between adjacent nodes in a flow constant (same lane y, same column spacing) so edges render as one clean line instead of a dogleg.
- **Align branch/secondary nodes on the exact same centerline as their parent.** Compute `child.x = parent.center_x - child.width/2`, don't eyeball it. A few pixels of misalignment turns a "straight down" edge into a visibly crooked diagonal.
- **One bend maximum per edge, ideally zero.** If a path needs more than one bend to dodge an obstacle, the layout is wrong — move the node, don't add bends.
- **No edge may cross through an unrelated icon's bounding box.** Check each edge path against every icon's `(x, y, width, height)` it isn't connected to.
- **No two edges may run on top of each other or visually merge.** Offset parallel flows via different exit/entry points or a waypoint.
- **Minimize edge crossings overall.** Order nodes in the direction data actually flows. Route unavoidable crossings (feedback/response paths) with a visible offset.
- **Keep spacing consistent, not just "enough."** Same minimum step size between every adjacent pair — 400px here and 250px there reads as sloppy even with no overlap.
- **Balance the composition on the canvas.** Don't leave one half dense and the other empty; size the canvas to the content plus a consistent margin.
- **Self-check before finishing:** trace each edge from source to target and verify (1) no icon crossed, (2) no edge overlap, (3) at most one bend, (4) endpoints flush with the icons.

## PNG Export Background
First element after root cells (lowest z-order):
```xml
<mxCell value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=none;" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="2400" height="1400" as="geometry" />
</mxCell>
```
Prevents a black background on PNG export. Use `strokeColor=none` (not `#E0E0E0`).

## AWS Icon Patterns (VERIFIED WORKING)

### resourceIcon (78x78, colored square frame)

| Service | resIcon | fillColor |
|---------|---------|-----------|
| Lambda | `mxgraph.aws4.lambda` | `#ED7100` |
| API Gateway | `mxgraph.aws4.api_gateway` | `#E7157B` |
| EventBridge | `mxgraph.aws4.eventbridge` | `#E7157B` |
| SNS | `mxgraph.aws4.sns` | `#E7157B` |
| SES | `mxgraph.aws4.simple_email_service` | `#DD344C` |
| Step Functions | `mxgraph.aws4.step_functions` | `#E7157B` |
| DynamoDB | `mxgraph.aws4.dynamodb` | `#C925D1` |
| RDS | `mxgraph.aws4.rds` | `#C925D1` |
| ElastiCache | `mxgraph.aws4.elasticache` | `#C925D1` |
| MSK | `mxgraph.aws4.managed_streaming_for_kafka` | `#8C4FFF` |
| S3 | `mxgraph.aws4.s3` | `#7AA116` |
| CloudFront | `mxgraph.aws4.cloudfront` | `#8C4FFF` |
| Route 53 | `mxgraph.aws4.route_53` | `#8C4FFF` |
| ECS | `mxgraph.aws4.ecs` | `#ED7100` |
| Fargate | `mxgraph.aws4.fargate` | `#ED7100` |
| EC2 | `mxgraph.aws4.ec2` | `#ED7100` |

Style template:
```
sketch=0;points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];outlineConnect=0;fontColor=#232F3E;fillColor=<COLOR>;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<SERVICE>
```

### productIcon (70x100, taller with service header bar)

| Service | prIcon |
|---------|--------|
| SQS | `mxgraph.aws4.sqs` |

Style template:
```
sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;strokeColor=#ffffff;fillColor=#232F3E;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;whiteSpace=wrap;fontSize=12;fontStyle=0;shape=mxgraph.aws4.productIcon;prIcon=mxgraph.aws4.<SERVICE>
```

### Standalone shapes (no resIcon needed)

| Shape | shape value | fillColor |
|-------|-------------|-----------|
| Client/Browser | `mxgraph.aws4.client` | `#232F3D` |
| Traditional Server | `mxgraph.aws4.traditional_server` | `#232F3D` |
| Firewall | `mxgraph.aws4.generic_firewall` | `#232F3D` |
| ALB | `mxgraph.aws4.application_load_balancer` | `#8C4FFF` |
| NLB | `mxgraph.aws4.network_load_balancer` | `#8C4FFF` |
| VPC Endpoint | `mxgraph.aws4.endpoints` | `#8C4FFF` |

### Group boundaries

| Group | grIcon | strokeColor |
|-------|--------|-------------|
| AWS Cloud | `mxgraph.aws4.group_aws_cloud_alt` | `#232F3E` |
| Account | `mxgraph.aws4.group_account` | `#CD2264` |
| On-premise | `mxgraph.aws4.group_on_premise` | `#5A6C86` |
| Corporate DC | `mxgraph.aws4.group_corporate_data_center` | `#388E3C` |
| VPC | `mxgraph.aws4.group_vpc2` | `#8C4FFF` |
| Subnet (public) | `mxgraph.aws4.group_security_group` | `#7AA116` |
| Subnet (private) | `mxgraph.aws4.group_security_group` | `#147EBA` |

Full group list: `references/aws-icons-common.md`. For a purely logical grouping with no AWS semantics, use a plain dashed box: `whiteSpace=wrap;html=1;fillColor=none;dashed=1;dashPattern=8 8`.

**Container nesting (CRITICAL for grouping):**
- ALL group/boundary shapes MUST include `container=1;dropTarget=1;` in their style
- Child cells inside a boundary MUST set `parent="<boundary-cell-id>"` instead of `parent="1"`
- Moving a boundary then moves all its children together
- Child geometry coordinates are **relative to the parent container**, not the canvas
- **Cross-container edges:** set the edge's `parent="1"`

## BROKEN Icons — DO NOT USE

- `resIcon=mxgraph.aws4.dynamodb_table` — renders as empty colored square
- `resIcon=mxgraph.aws4.dynamodb_stream` — renders as empty colored square
- `resIcon=mxgraph.aws4.general_saml_token` — renders as black square
- `resIcon=mxgraph.aws4.endpoint` — may not render
- `resIcon=mxgraph.aws4.kinesis_data_streams` — unreliable

**Alternatives:**
- DynamoDB tables/streams → `resIcon=mxgraph.aws4.dynamodb` with descriptive labels
- External systems → `shape=mxgraph.aws4.traditional_server`
- Browsers/clients → `shape=mxgraph.aws4.client`

## Icon Name Gotchas — CRITICAL

draw.io stencil names do NOT always match current AWS service names. Renamed services keep their legacy stencil names:

| AWS Service Name | draw.io resIcon name | Why |
|---|---|---|
| Amazon OpenSearch Service | `elasticsearch_service` | Renamed from Elasticsearch in 2021; `opensearch_service` also works |
| Amazon EventBridge | `eventbridge` | Was CloudWatch Events |
| AWS Fargate | `fargate` | Correct |
| VPC Peering | `peering` | Resource-level: `shape=mxgraph.aws4.peering;strokeColor=none` — NOT `vpc_peering` or `peering_connection` (blank squares) |
| Amazon MSK | `managed_streaming_for_kafka` | NOT `msk` (blank square) |
| IAM Identity Center | `single_sign_on` | NOT `iam_identity_center` (blank square) |

**Rule:** verify icon names from the reference files. If a service icon renders as an empty box, the stencil name is wrong. Canonical names live in the draw.io source at `src/main/webapp/js/diagramly/sidebar/Sidebar-AWS4.js` (or `Sidebar-AWS3D.js` for the legacy 3D library, `Sidebar-AlliedTelesis.js` for the hardware image library).

**Fallback for unmapped services:** if a service is in no reference file, use the generic AWS cloud icon with the service name as label:
```
sketch=0;outlineConnect=0;fontColor=#232F3E;fillColor=#232F3E;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.general_AWScloud
```
Never render an unknown service as a plain colored rectangle with no label.

## Audience Mode

Before generating, assess the target audience:
- **Technical**: service names, protocol labels (HTTPS, gRPC), CIDR blocks, instance types
- **Non-technical**: action labels ("Store Data", "Send Notification"), no implementation details, numbered flow (① ② ③)

If unclear, ask: "Technical audience or executive/non-technical?"

### Numbered flow edges (for non-technical mode)
- Flow A: ① → ② → ③ → ④ (white circled numbers)
- Flow B: ❶ → ❷ → ❸ → ❹ (black circled numbers for a second flow)

Edge label style: `value="①"` with `fontSize=14;fontStyle=1;labelBackgroundColor=#ffffff;`

## Companion Guide

After generating the .drawio file, also generate a markdown guide:
- Same filename with `.md` extension (`serverless-api.drawio` + `serverless-api.md`)
- Contents: diagram title, flow description (numbered steps matching edge labels), service list with purpose, key design decisions

## Two-Step Edit Approach

1. **Export to PNG** with the draw.io CLI (see Export)
2. **Review the PNG** visually — empty/broken icons, overlapping edges, misaligned labels
3. **Fix** the .drawio XML and re-export

This catches rendering problems (wrong stencil names, broken styles) that are invisible in raw XML.

## Validation Step

After generating XML, verify:
1. Every `resIcon=` value exists in the reference files
2. Service-level icons have `strokeColor=#ffffff`
3. Resource-level icons have `strokeColor=none`
4. No XML comments present
5. All cell IDs are unique
6. Every edge has `<mxGeometry relative="1" as="geometry" />`
7. No guessed stencil names — all verified against reference files
8. Every edge has both `source` and `target` referencing valid cell IDs (no floating edges)
9. All group/boundary shapes include `container=1;dropTarget=1;`
10. Children inside boundaries use `parent="<boundary-id>"` (not `parent="1"`)

## Export

### Multi-page Diagrams
For complex architectures, use multiple pages in one .drawio file:
```xml
<mxfile>
  <diagram id="overview" name="Overview">...</diagram>
  <diagram id="networking" name="Networking Detail">...</diagram>
  <diagram id="data-flow" name="Data Flow">...</diagram>
</mxfile>
```
- Page 1: high-level overview (service-level icons only)
- Page 2+: detail views (resource-level icons, subnet layouts)

### Export CLI

| Platform | CLI Path |
|----------|----------|
| Windows | `"C:\Program Files\draw.io\draw.io.exe"` |
| macOS | `/Applications/draw.io.app/Contents/MacOS/draw.io` |
| Linux | `drawio` (on PATH via snap/apt) |

```
<CLI> -x -f <format> -e -b 10 -o <output> <input>
```

Flags: `-x` export, `-f` format (png/svg/pdf), `-e` embed diagram XML, `-b 10` border.

Exported files use a double extension: `name.drawio.png` — signals embedded XML, re-editable in draw.io. If the CLI isn't installed, say so and hand back the `.drawio` path rather than silently skipping the export.

## XML Well-formedness (CRITICAL)

- **NEVER include XML comments (`<!-- -->`)** — they cause parse errors
- Escape special characters: `&amp;` `&lt;` `&gt;` `&quot;`
- Unique `id` on every mxCell
- Every edge MUST have `<mxGeometry relative="1" as="geometry" />` as a child
- Root structure requires cells `id="0"` (root) and `id="1"` (default layer, `parent="0"`)
- Large diagrams: build the file in several Write/Edit passes (header + left, middle, right, bottom + close) rather than one giant blob

## Official Reference

- XML reference: https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-reference.md
- Style reference: https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/style-reference.md
