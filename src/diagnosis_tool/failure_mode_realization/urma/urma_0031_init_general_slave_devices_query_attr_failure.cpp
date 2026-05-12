#include "urma_0031_init_general_slave_devices_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0031InitGeneralSlaveDevicesQueryAttrFailure> g_urma("urma_0031");

bool Urma0031InitGeneralSlaveDevicesQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get slave device info"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0031InitGeneralSlaveDevicesQueryAttrFailure::GetName() const
{
    return "init_general_slave_devices 查询属性失败";
}

std::string Urma0031InitGeneralSlaveDevicesQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `urma_cmd_user_ctl(&bond_ctx->v_ctx, &in, &out, &data)`；该路径返回 -1";
}

RootCause Urma0031InitGeneralSlaveDevicesQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0031InitGeneralSlaveDevicesQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0031InitGeneralSlaveDevicesQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get slave device info";
}

std::string Urma0031InitGeneralSlaveDevicesQueryAttrFailure::GetId() const
{
    return "urma_0031";
}
} // namespace diag
