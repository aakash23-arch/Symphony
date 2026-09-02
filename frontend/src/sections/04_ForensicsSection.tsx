import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { TickerMarquee } from '../design-system/TickerMarquee';
import { SystemTimeline, TimelineItem } from '../design-system/SystemTimeline';
import { ExpertPipelineDiagram } from '../components/storytelling/ExpertPipelineDiagram';
import { CountUp } from '../design-system/CountUp';

const PATTERN_TIMELINE: TimelineItem[] = [
  { id: 1, label: 'Live human voice', timestamp: '00:00 – 00:41', detail: 'Small talk, genuine prosody, matches enrolled speaker baseline.', severity: 'SAFE', kind: 'BASELINE' },
  { id: 2, label: 'Synthetic segment localized', timestamp: '00:41 – 00:45', detail: 'Vocoder periodicity flagged by E1 and E2. A cloned phrase spliced into an otherwise genuine call.', severity: 'CRITICAL', kind: 'ANOMALY' },
  { id: 3, label: 'Live human voice resumes', timestamp: '00:45 – 01:42', detail: 'Acoustics return to baseline — the splice is isolated, not the whole call.', severity: 'SAFE', kind: 'BASELINE' },
];

const ATTACK_CLASSES = [
  { id: 'TTS', label: 'Text-to-speech', detail: 'Text converted into the target voice.' },
  { id: 'VC', label: 'Voice conversion', detail: "Attacker's own voice transformed toward the target." },
  { id: 'RP', label: 'Replay', detail: 'A recording played back into the live call.' },
];

export const ForensicsSection: React.FC = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"]
  });

  const layerY = useTransform(scrollYProgress, [0, 1], [100, -100]);

  return (
    <section
      id="forensics"
      ref={sectionRef}
      className="relative py-20 px-4 sm:px-8 border-b border-border bg-surface-elevated overflow-hidden"
    >
      <div className="max-w-[1200px] mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        
        <div className="space-y-8 z-10">
          <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary">
            <span>PHASE II–III // FORENSICS</span>
          </div>

          <h2 className="display-lg text-fg font-bold tracking-tight leading-[1.1]">
            Beneath the <br/>
            <span className="serif-italic font-normal">surface.</span>
          </h2>

          <p className="text-lg text-fg-secondary max-w-sm">
            Every call is checked against three named attack classes. A defender who only tests one type of fake is easy to fool.
          </p>
        </div>

        <motion.div
          style={{ y: layerY }}
          className="relative h-[420px] w-full flex flex-col justify-center items-end"
        >
          {ATTACK_CLASSES.map((attack, i) => (
            <motion.div
              key={attack.id}
              initial={{ x: 50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ delay: i * 0.1, duration: 0.8 }}
              className="rounded-sm w-full max-w-md h-32 border border-border bg-surface mb-[-40px] shadow-sm flex flex-col justify-between p-4 transform hover:-translate-x-4 transition-transform duration-200 ease-out"
              style={{ zIndex: 10 - i }}
            >
              <div className="font-mono text-xs text-fg-tertiary uppercase">
                Attack class — {attack.id}
              </div>
              <div className="font-mono text-sm font-bold uppercase">
                {attack.label}
              </div>
              <p className="text-xs text-fg-secondary">{attack.detail}</p>
            </motion.div>
          ))}
        </motion.div>

      </div>

      {/* Partial-spoof localization */}
      <div className="max-w-[1200px] mx-auto w-full mt-16">
        <div className="max-w-xl mb-10">
          <h3 className="display-md text-fg font-bold tracking-tight uppercase">
            Not the whole call — <span className="serif-italic font-normal normal-case text-fg-secondary">just the splice.</span>
          </h3>
          <p className="text-fg-secondary mt-3">
            A real attacker doesn't clone an entire conversation — they splice one cloned phrase into an
            otherwise genuine call. Symphony localizes the synthetic seconds instead of scoring the whole call.
          </p>
        </div>
        <SystemTimeline items={PATTERN_TIMELINE} maxHeight="max-h-none" />
      </div>

      {/* Case-study evidence panel — scripted demo scenario */}
      <div className="max-w-[1200px] mx-auto w-full mt-16">
        <div className="rounded-sm overflow-hidden border border-border bg-surface">
          <div className="border-b border-border py-3">
            <TickerMarquee text="CALL SESSION EVIDENCE  SPEAKER VERIFICATION  LIVENESS CHECK  BELIEF FUSION  " />
          </div>
          <div className="p-6 border-b border-border">
            <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-2">
              Demo scenario
            </div>
            <p className="text-sm text-fg-secondary max-w-2xl">
              A cloned "CEO" voice, sent over a noisy G.711 line, tells an employee:
              <span className="italic text-fg"> "Transfer ₹25 lakh immediately. Do not call me back — I'm in a meeting."</span>
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 p-6 border-b border-border">
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Voice Integrity</div>
              <div className="font-mono text-sm font-bold text-state-critical">
                <CountUp to={81} suffix="% suspicious" />
              </div>
            </div>
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Speaker Match</div>
              <div className="font-mono text-sm font-bold text-fg">
                <CountUp to={54} suffix="%" />
              </div>
            </div>
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Social Engineering</div>
              <div className="font-mono text-sm font-bold text-state-critical">HIGH</div>
            </div>
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Transaction Risk</div>
              <div className="font-mono text-sm font-bold text-state-critical">CRITICAL</div>
            </div>
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Final Risk</div>
              <div className="font-mono text-sm font-bold text-state-critical">
                <CountUp to={96} suffix="%" />
              </div>
            </div>
            <div>
              <div className="font-mono text-micro-label uppercase tracking-widest text-fg-tertiary mb-1">Action</div>
              <div className="font-mono text-sm font-bold text-fg">HOLD + CALL BACK TO VERIFY</div>
            </div>
          </div>
          <div className="p-6">
            <ExpertPipelineDiagram />
          </div>
        </div>
      </div>
    </section>
  );
};
