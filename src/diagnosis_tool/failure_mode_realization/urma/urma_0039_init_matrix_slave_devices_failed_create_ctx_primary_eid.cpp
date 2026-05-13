#include "urma_0039_init_matrix_slave_devices_failed_create_ctx_primary_eid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid> g_urma("urma_0039");

bool Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create ctx for primary eid[%]"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::GetName() const
{
    return "init_matrix_slave_devices Failed to create ctx for primary eid";
}

std::string Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create ctx for primary eid[%]";
}

std::string Urma0039InitMatrixSlaveDevicesFailedCreateCtxPrimaryEid::GetId() const
{
    return "urma_0039";
}
} // namespace diag
