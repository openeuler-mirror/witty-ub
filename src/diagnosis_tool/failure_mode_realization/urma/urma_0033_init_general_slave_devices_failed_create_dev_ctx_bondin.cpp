#include "urma_0033_init_general_slave_devices_failed_create_dev_ctx_bondin.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin> g_urma("urma_0033");

bool Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create dev ctx % in bonding"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::GetName() const
{
    return "init_general_slave_devices Failed to create dev ctx % in bondin";
}

std::string Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "init_slave_context_fd(bond_ctx)";
}

RootCause Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create dev ctx % in bonding";
}

std::string Urma0033InitGeneralSlaveDevicesFailedCreateDevCtxBondin::GetId() const
{
    return "urma_0033";
}
} // namespace diag
