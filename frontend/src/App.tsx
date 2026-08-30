import React from 'react';

import { ScrollProgress } from './design-system/ScrollProgress';
import { HeaderBar } from './panels/HeaderBar';
import {
  HeroSection,
  ProblemSection,
  RawSignalSection,
  PipelineSection,
  ForensicLayerSection,
  BeliefTrajectorySection,
  ContextDecisionSection,
  LiveDetectionSection,
  PolicyActionSection,
  ProtectionSection,
  AssuranceSection,
  ScenarioMatrixSection,
  TechnicalArchitectureSection,
  ClosingSection,
  NarrativeFooter,
} from './sections';
import { SessionProvider } from './state/SessionProvider';

/**
 * Symphony Editorial Product Narrative & Live Detection Console.
 *
 * Storytelling Hierarchy:
 *  - Section 00: Hero (Voice sounds real — that doesn't mean it is)
 *  - Section 01: The Problem (A voice is no longer proof of identity)
 *  - Section 02: Raw Signal (Every call starts as data)
 *  - Section 03: The Five-Layer Symphony Pipeline (L1–L5 stages)
 *  - Section 04: The Forensic Layer (One signal, multiple questions — E1–E6 ensemble)
 *  - Section 05: The Signal Becomes a Belief (Temporal trajectory & convergence)
 *  - Section 06: Context Changes the Decision (Voice + Call + Transaction fusion)
 *  - Section 07: Live Detection Console (Operational real-time defense console)
 *  - Section 08: The Decision (The output is an action — policy directives)
 *  - Section 09: Protection (Real-time financial hold & verification sequence)
 *  - Section 10: Assurance (Cryptographic SHA-256 evidence chain & dossier)
 *  - Section 11: Demo Scenarios (Interactive test vectors & live mic)
 *  - Section 12: Technical Architecture (End-to-end processing topology)
 *  - Section 13: Closing (Don't trust voice alone — trust the signal behind it)
 *  - Footer: Brand, simulation disclaimer, and raw audio privacy notice
 */
const Dashboard: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col bg-background text-fg selection:bg-accent/30 selection:text-white">
      <ScrollProgress />
      <HeaderBar />

      <main className="flex-1 px-4 py-8 sm:px-6 lg:px-8 max-w-[1600px] w-full mx-auto space-y-16">
        <HeroSection />
        <ProblemSection />
        <RawSignalSection />
        <PipelineSection />
        <ForensicLayerSection />
        <BeliefTrajectorySection />
        <ContextDecisionSection />
        <LiveDetectionSection />
        <PolicyActionSection />
        <ProtectionSection />
        <AssuranceSection />
        <ScenarioMatrixSection />
        <TechnicalArchitectureSection />
        <ClosingSection />
      </main>

      <NarrativeFooter />
    </div>
  );
};

export const App: React.FC = () => (
  <SessionProvider>
    <Dashboard />
  </SessionProvider>
);


