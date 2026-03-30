import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { transformBusinessUnits, transformHierarchyTree, type TreeNodeData } from '../utils/transformers'

// Fallback data if API unavailable
const FALLBACK_BUS: Array<{ id: string | null; name: string }> = [
  { id: null, name: 'All' },
  { id: 'marsh', name: 'Marsh' },
  { id: 'mercer', name: 'Mercer' },
  { id: 'guy_carpenter', name: 'Guy Carpenter' },
  { id: 'oliver_wyman', name: 'Oliver Wyman' },
  { id: 'mmc_corporate', name: 'MMC Corporate' },
]

const FALLBACK_HIERARCHIES: Record<string, TreeNodeData[]> = {
  geography: [
    {
      id: 'global',
      name: 'Global',
      children: [
        {
          id: 'americas',
          name: 'Americas',
          children: [
            {
              id: 'us',
              name: 'United States',
              children: [
                { id: 'us_ne', name: 'US Northeast' },
                { id: 'us_se', name: 'US Southeast' },
                { id: 'us_mw', name: 'US Midwest' },
                { id: 'us_w', name: 'US West' },
              ],
            },
            { id: 'canada', name: 'Canada' },
            { id: 'latam', name: 'Latin America' },
          ],
        },
        {
          id: 'emea',
          name: 'EMEA',
          children: [
            { id: 'uk_ireland', name: 'UK & Ireland' },
            { id: 'europe', name: 'Continental Europe' },
            { id: 'mena', name: 'Middle East & Africa' },
          ],
        },
        {
          id: 'apac',
          name: 'Asia Pacific',
          children: [
            { id: 'anz', name: 'Australia & NZ' },
            { id: 'japan', name: 'Japan' },
            { id: 'india', name: 'India' },
            { id: 'singapore', name: 'Singapore' },
          ],
        },
      ],
    },
  ],
  segment: [
    {
      id: 'all_seg',
      name: 'All Segments',
      children: [
        { id: 'commercial', name: 'Commercial' },
        { id: 'consumer', name: 'Consumer' },
        { id: 'specialty', name: 'Specialty' },
        { id: 'government', name: 'Government' },
      ],
    },
  ],
  lob: [
    {
      id: 'all_lob',
      name: 'All LOBs',
      children: [
        { id: 'risk_advisory', name: 'Risk Advisory' },
        { id: 'consulting', name: 'Consulting' },
        { id: 'reinsurance', name: 'Reinsurance' },
        { id: 'wealth', name: 'Wealth' },
        { id: 'dna', name: 'D&A' },
      ],
    },
  ],
  costcenter: [
    {
      id: 'all_cc',
      name: 'All Cost Centers',
      children: [
        { id: 'client_ops', name: 'Client Operations' },
        { id: 'corporate', name: 'Corporate' },
        { id: 'technology', name: 'Technology' },
        { id: 'executive', name: 'Executive' },
      ],
    },
  ],
}

export function useDimensions() {
  const [businessUnits, setBusinessUnits] = useState<Array<{ id: string | null; name: string }>>(FALLBACK_BUS)
  const [hierarchies, setHierarchies] = useState<Record<string, TreeNodeData[]>>(FALLBACK_HIERARCHIES)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.gateway.get('/dimensions/business-units').catch(() => null),
      api.gateway.get('/dimensions/hierarchies/geography').catch(() => null),
      api.gateway.get('/dimensions/hierarchies/segment').catch(() => null),
      api.gateway.get('/dimensions/hierarchies/lob').catch(() => null),
      api.gateway.get('/dimensions/hierarchies/costcenter').catch(() => null),
    ]).then(([bus, geo, seg, lob, cc]) => {
      if (bus) setBusinessUnits(transformBusinessUnits(bus))
      const h: Record<string, TreeNodeData[]> = {}
      if (geo) h.geography = transformHierarchyTree(geo)
      if (seg) h.segment = transformHierarchyTree(seg)
      if (lob) h.lob = transformHierarchyTree(lob)
      if (cc) h.costcenter = transformHierarchyTree(cc)
      if (Object.keys(h).length > 0) setHierarchies(h)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  return { businessUnits, hierarchies, loading }
}
