#include "kvcache_conn_fault_028_008.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_008> g_kvcacheconnfault("kvcache_conn_fault_028_008");

bool KvcacheConnFault028_008::IsValid(const std::vector<std::string> &fields)
{
    // 来源：kvcache_conn_fault_mode.md:L1028-1047
    // 错误码1009 K_URMA_CONNECT_FAILED：URMA建连失败
    // access log识别：status_code（第8列）code=1009
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    if (statusCode == 1009) {
        return true;
    }
    // runtime log识别：URMA建连失败也可能从message中看出
    // 但1009是access log专属错误码，runtime log中通过[URMA_前缀识别交由028父节点处理
    // 来源：08手册:L304
    return false;
}

std::string KvcacheConnFault028_008::GetName() const
{
    return "错误码1009 K_URMA_CONNECT_FAILED（URMA建连失败）。";
}

std::string KvcacheConnFault028_008::GetRootCauseDesc() const
{
    return "URMA建连失败，可能UB端口down或设备节点缺失，属于URMA责任"
           "（08手册:L304）。";
}

RootCause KvcacheConnFault028_008::AnalyzeRootCause()
{
    // 028子故障不作为叶子故障，会与urma相关的故障进行关联
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_008::GetFixSuggDesc() const
{
    return "ifconfig ub0查端口up/down；ls /dev/ub*看设备节点是否存在"
           "（08手册:L304）。";
}

std::string KvcacheConnFault028_008::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L304）：access log中status_code（第8列）"
           "code=1009（K_URMA_CONNECT_FAILED）；或ifconfig ub0/ubinfo/ls /dev/ub*"
           "确认端口和设备节点状态（08手册:L304）。";
}

std::string KvcacheConnFault028_008::GetId() const
{
    return "kvcache_conn_fault_028_008";
}
} // namespace diag
