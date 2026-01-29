/**
 * Dashboard Overview para Operador
 * Métricas de atendimento e pedidos
 */

import { useState, useEffect } from 'react'
import { LayoutDashboard, Package, RefreshCcw, MessageSquare, AlertTriangle, Clock, Truck, CheckCircle } from 'lucide-react'

export default function OperatorDashboardOverview() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMetrics()
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchMetrics = async () => {
    try {
      setLoading(true)

      // Buscar métricas em paralelo usando api.js
      const apiUrl = import.meta.env.VITE_API_URL || 'http://192.168.10.156:8000/api'
      const token = localStorage.getItem('token')

      // Buscar pedidos de hoje (contém todos os status) e conversas
      const [todayOrdersRes, conversationsRes] = await Promise.all([
        fetch(`${apiUrl}/orders/today`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${apiUrl}/my-conversations`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ])

      const todayOrders = todayOrdersRes.ok ? await todayOrdersRes.json() : []
      const conversations = conversationsRes.ok ? await conversationsRes.json() : []

      setMetrics({
        orders: {
          pending: todayOrders.filter(o => o.status === 'pending').length,
          processing: todayOrders.filter(o => o.status === 'preparing').length,
          dispatched: todayOrders.filter(o => o.status === 'dispatched').length,
          delivered: todayOrders.filter(o => o.status === 'delivered').length,
          total: todayOrders.length
        },
        conversations: {
          active: conversations.length, // Todas as conversas são consideradas ativas
          waiting: 0, // Sistema de atribuição não implementado ainda
          mine: 0, // Sistema de atribuição não implementado ainda
          total: conversations.length
        }
      })
    } catch (error) {
      console.error('Erro ao buscar métricas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
        <p className="mt-3 text-sm text-gray-600">Carregando métricas...</p>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Erro ao carregar métricas
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Atendimento</h2>
        <p className="text-sm text-gray-600">Pedidos e conversas em andamento</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500">Pendentes</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900">{metrics.orders.pending}</p>
              <p className="mt-1 text-xs text-gray-500">Aguardando aprovacao</p>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-amber-700">
              <Clock className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500">Em preparo</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900">{metrics.orders.processing}</p>
              <p className="mt-1 text-xs text-gray-500">Sendo preparados</p>
            </div>
            <div className="rounded-lg bg-primary-50 p-3 text-primary-700">
              <RefreshCcw className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500">Em rota</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900">{metrics.orders.dispatched || 0}</p>
              <p className="mt-1 text-xs text-gray-500">Saiu para entrega</p>
            </div>
            <div className="rounded-lg bg-purple-50 p-3 text-purple-700">
              <Truck className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500">Entregues</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900">{metrics.orders.delivered || 0}</p>
              <p className="mt-1 text-xs text-gray-500">Finalizados hoje</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-green-700">
              <CheckCircle className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500">Total hoje</p>
              <p className="mt-1 text-3xl font-semibold text-gray-900">{metrics.orders.total}</p>
              <p className="mt-1 text-xs text-gray-500">Todos os status</p>
            </div>
            <div className="rounded-lg bg-blue-50 p-3 text-blue-700">
              <Package className="h-5 w-5" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-gray-900">Pedidos de Hoje</h3>
          <p className="text-sm text-gray-500">Resumo por status</p>
          <div className="mt-4 space-y-2">
            {[
              { label: 'Pendentes', value: metrics.orders.pending, color: 'text-amber-600' },
              { label: 'Em preparo', value: metrics.orders.processing, color: 'text-primary-600' },
              { label: 'Em rota', value: metrics.orders.dispatched || 0, color: 'text-purple-600' },
              { label: 'Entregues', value: metrics.orders.delivered || 0, color: 'text-green-600' },
              { label: 'Total', value: metrics.orders.total, color: 'text-gray-900' },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-medium text-gray-700">{row.label}</span>
                <span className={`text-sm font-semibold ${row.color}`}>{row.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-gray-900">Conversas</h3>
          <p className="text-sm text-gray-500">Resumo</p>
          <div className="mt-4 space-y-2">
            {[
              { label: 'Total', value: metrics.conversations.total },
              { label: 'Ativas', value: metrics.conversations.active },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-medium text-gray-700">{row.label}</span>
                <span className="text-sm font-semibold text-gray-900">{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end">
        <button
          onClick={fetchMetrics}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Atualizar
        </button>
      </div>
    </div>
  )
}
