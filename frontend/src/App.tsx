import { useState } from 'react'
import Header from './components/Header'
import KPICards from './components/KPICards'
import DeploymentTable from './components/DeploymentTable'
import CommandBar from './components/CommandBar'
import WorkflowDesigner from './components/WorkflowDesigner'
import { ThemeProvider } from './contexts/ThemeContext'

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'agent-workflows'>('dashboard')

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors">
        <Header activeTab={activeTab} onTabChange={setActiveTab} />
        {activeTab === 'dashboard' ? (
          <>
            <main className="container mx-auto px-4 py-8 max-w-7xl">
              <KPICards />
              <div className="mt-8">
                <DeploymentTable />
              </div>
            </main>
            <CommandBar />
          </>
        ) : (
          <WorkflowDesigner />
        )}
      </div>
    </ThemeProvider>
  )
}

export default App

