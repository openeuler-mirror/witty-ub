#include "kvcache_conn_fault_041.h"
#include "../failure_mode_factory.h"
#include "kvcache_conn_utils.h"

namespace diag {

static AutoRegister<KvcacheConnFault041> g_KvcacheConnFault041("kvcache_conn_fault_041");

KvcacheConnFault041::KvcacheConnFault041() noexcept
{
}

bool KvcacheConnFault041::IsValid()
{
    // 来源: references/kvcache_conn_fault_mode.md L745-L758
    // 来源: 10-customer-fault-scenarios.md L539-L540
    // Case 1: [TCP_CONNECT_FAILED]
    // 来源: references/kvcache_conn_fault_mode.md L745-L758
    std::string grepOutput0 = kvcache_conn_utils::RunCommand(
        R"(grep '\[TCP_CONNECT_FAILED\]' $LOG/ds_client_<pid>.INFO.log | head 2>/dev/null)");
    bool case0_matched = !grepOutput0.empty();
    // Case 2: 对端端口LISTEN
    // 来源: references/kvcache_conn_fault_mode.md L745-L758
    std::string cmdOutput1 = kvcache_conn_utils::RunCommand(
        R"(ss -tnlp | grep 31402 2>/dev/null)");
    bool case1_matched = !cmdOutput1.empty();
    return case0_matched || case1_matched;
}

std::string KvcacheConnFault041::GetName() const
{
    return "TCP建连失败（对端LISTEN）";
}

std::string KvcacheConnFault041::GetRootCauseDesc() const
{
    return "主机/网络，防火墙/路由不通";
}

RootCause KvcacheConnFault041::AnalyzeRootCause()
{
    return RootCause(true, "主机/网络，防火墙/路由不通");
}

std::string KvcacheConnFault041::GetFixSuggDesc() const
{
    return "iptables -L -n；nc -zv <worker> <port>；删除iptables DROP规则；检查安全组";
}

std::string KvcacheConnFault041::GetValidationMethodDesc() const
{
    return "INFO log含[TCP_CONNECT_FAILED]且对端端口LISTEN";
}

std::string KvcacheConnFault041::GetId() const
{
    return "kvcache_conn_fault_041";
}

} // namespace diag