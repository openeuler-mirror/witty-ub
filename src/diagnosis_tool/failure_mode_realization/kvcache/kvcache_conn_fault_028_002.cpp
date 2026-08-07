#include "kvcache_conn_fault_028_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_002> g_kvcacheconnfault("kvcache_conn_fault_028_002");

bool KvcacheConnFault028_002::IsValid(const std::vector<std::string> &fields)
{
    // 来源：kvcache_conn_fault_mode.md:L901-915
    // 通过日志关键字[URMA_NEED_CONNECT] + instanceId不变判断UB链路不稳
    // 注意：需要在运行时进一步判断instanceId是否变化来区分028_001和028_002
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[URMA_NEED_CONNECT]") != std::string::npos);
    // 与028_001共用URMA_NEED_CONNECT关键字，运行时根据instanceId是否变化区分：
    // instanceId变化 → 028_001（对端重启）；instanceId不变 → 028_002（链路不稳）
    // 来源：08手册:L298
}

std::string KvcacheConnFault028_002::GetName() const
{
    return "URMA_NEED_CONNECT持续 + instanceId不变（UB链路不稳）。";
}

std::string KvcacheConnFault028_002::GetRootCauseDesc() const
{
    return "UB链路不稳，需区分是硬件/驱动问题还是端口/交换机抖动"
           "（08手册:L298）。";
}

RootCause KvcacheConnFault028_002::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_002::GetFixSuggDesc() const
{
    return "检查UB端口状态和交换机；若伴POLL_ERROR/RECREATE_JFS则需联系URMA/UB运维"
           "（08手册:L298）。";
}

std::string KvcacheConnFault028_002::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L298, 10案例:L124）：匹配[URMA_NEED_CONNECT]"
           "持续出现且instanceId不变。";
}

std::string KvcacheConnFault028_002::GetId() const
{
    return "kvcache_conn_fault_028_002";
}
} // namespace diag
