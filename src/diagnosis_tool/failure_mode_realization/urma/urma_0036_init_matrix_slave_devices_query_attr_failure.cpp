#include "urma_0036_init_matrix_slave_devices_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0036InitMatrixSlaveDevicesQueryAttrFailure> g_urma("urma_0036");

bool Urma0036InitMatrixSlaveDevicesQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get topo info by bonding eid"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0036InitMatrixSlaveDevicesQueryAttrFailure::GetName() const
{
    return "init_matrix_slave_devices 查询属性失败";
}

std::string Urma0036InitMatrixSlaveDevicesQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `topo_info == NULL`；该路径返回 -1";
}

RootCause Urma0036InitMatrixSlaveDevicesQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0036InitMatrixSlaveDevicesQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0036InitMatrixSlaveDevicesQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get topo info by bonding eid";
}

std::string Urma0036InitMatrixSlaveDevicesQueryAttrFailure::GetId() const
{
    return "urma_0036";
}
} // namespace diag
