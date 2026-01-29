/**
 * Painel de Pedidos Pendentes para Operador
 * Aprovar, rejeitar e gerenciar pedidos do WhatsApp Bot
 */

import { useState, useEffect } from 'react'
import { RefreshCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import api, { getOrdersPending } from '../../services/api'

export default function PendingOrdersPanel() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [actionType, setActionType] = useState(null) // 'approve' or 'reject'
  const [rejectReason, setRejectReason] = useState('')
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const data = await getOrdersPending()
      setOrders(data)
    } catch (error) {
      console.error('Erro ao buscar pedidos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (orderId) => {
    try {
      setProcessing(true)
      await api.post(`/orders/${orderId}/approve`)
      await fetchOrders()
      setSelectedOrder(null)
      setActionType(null)
      toast.success('Pedido aprovado com sucesso!')
    } catch (error) {
      console.error('Erro ao aprovar:', error)
      toast.error('Erro ao aprovar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const handleReject = async (orderId) => {
    if (!rejectReason.trim()) {
      toast.error('Por favor, informe o motivo da rejeição')
      return
    }

    try {
      setProcessing(true)
      await api.post(`/orders/${orderId}/reject`, { reason: rejectReason })
      await fetchOrders()
      setSelectedOrder(null)
      setActionType(null)
      setRejectReason('')
      toast.success('Pedido rejeitado')
    } catch (error) {
      console.error('Erro ao rejeitar:', error)
      toast.error('Erro ao rejeitar pedido')
    } finally {
      setProcessing(false)
    }
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  const formatDateTime = (isoString) => {
    const date = new Date(isoString)
    return date.toLocaleString('pt-BR')
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-gray-200 border-t-primary-600" />
        <p className="mt-3 text-sm text-gray-600">Carregando pedidos...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Pedidos pendentes</h2>
          <p className="text-sm text-gray-600">Aprovar ou rejeitar pedidos do WhatsApp</p>
        </div>
        <button
          onClick={fetchOrders}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          <RefreshCcw className="h-4 w-4" />
          Atualizar
        </button>
      </div>

      {/* Lista de Pedidos */}
      {orders.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-10 text-center shadow-sm">
          <p className="text-base font-medium text-gray-900">Nenhum pedido pendente</p>
          <p className="mt-1 text-sm text-gray-600">Todos os pedidos foram processados.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {orders.map((order) => (
            <div key={order.id} className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              {/* Header do Pedido */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Pedido #{order.order_number || order.id}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {formatDateTime(order.created_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setSelectedOrder(order)
                      setActionType('approve')
                    }}
                    className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                  >
                    Aprovar
                  </button>
                  <button
                    onClick={() => {
                      setSelectedOrder(order)
                      setActionType('reject')
                    }}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                  >
                    Rejeitar
                  </button>
                </div>
              </div>

              {/* Informações do Cliente */}
              <div className="rounded-lg bg-gray-50 p-4 mb-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Cliente</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Nome:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      {order.customer_name || 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Telefone:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      {order.customer_phone || 'N/A'}
                    </span>
                  </div>
                  {order.delivery_address && (
                    <div className="col-span-2">
                      <span className="text-gray-500">Endereço:</span>
                      <span className="ml-2 font-medium text-gray-900">
                        {order.delivery_address}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Itens do Pedido */}
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-2">Itens</h4>
                <div className="space-y-2">
                  {order.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center rounded-lg bg-gray-50 p-2">
                      <div>
                        <span className="font-medium">{item.product_name || item.name}</span>
                        <span className="ml-2 text-sm text-gray-500">x{item.quantity}</span>
                      </div>
                      <span className="font-bold">{formatCurrency(item.total || item.price * item.quantity)}</span>
                    </div>
                  )) || (
                    <p className="text-sm text-gray-500">Nenhum item especificado</p>
                  )}
                </div>
              </div>

              {/* Total */}
              <div className="flex items-center justify-between border-t border-gray-200 pt-4">
                <span className="text-sm font-semibold text-gray-900">Total</span>
                <span className="text-xl font-semibold text-gray-900">
                  {formatCurrency(order.total_amount || order.total || 0)}
                </span>
              </div>

              {/* Forma de Pagamento */}
              {order.payment_method && (
                <div className="mt-2 text-sm text-gray-600">
                  Pagamento: <span className="font-medium text-gray-900">{order.payment_method}</span>
                </div>
              )}

              {/* Observações */}
              {order.notes && (
                <div className="mt-4 rounded-lg bg-gray-50 p-3">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium text-gray-900">Observações:</span> {order.notes}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal de Confirmação */}
      {selectedOrder && actionType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 p-4">
          <div className="w-full max-w-md overflow-hidden rounded-xl bg-white shadow-xl">
            {/* Header */}
            <div className={`border-b border-gray-200 p-6 ${actionType === 'approve' ? 'bg-green-50' : 'bg-red-50'}`}>
              <h3 className="text-lg font-semibold text-gray-900">
                {actionType === 'approve' ? 'Aprovar pedido' : 'Rejeitar pedido'}
              </h3>
              <p className="mt-1 text-sm text-gray-600">
                Pedido #{selectedOrder.order_number || selectedOrder.id}
              </p>
            </div>

            {/* Content */}
            <div className="p-6">
              {actionType === 'approve' ? (
                <div>
                  <p className="text-sm text-gray-700">Confirmar aprovação deste pedido?</p>
                  <div className="mt-3 rounded-lg bg-gray-50 p-3 text-sm">
                    Total: <span className="font-semibold text-gray-900">{formatCurrency(selectedOrder.total_amount || 0)}</span>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Motivo da Rejeição:
                  </label>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-red-500 focus:ring-red-500"
                    rows="4"
                    placeholder="Ex: Produto indisponível, endereço fora da área de entrega, etc."
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex gap-3 border-t border-gray-200 bg-gray-50 p-6">
              <button
                onClick={() => {
                  setSelectedOrder(null)
                  setActionType(null)
                  setRejectReason('')
                }}
                disabled={processing}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (actionType === 'approve') {
                    handleApprove(selectedOrder.id)
                  } else {
                    handleReject(selectedOrder.id)
                  }
                }}
                disabled={processing}
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${
                  actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {processing ? 'Processando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
