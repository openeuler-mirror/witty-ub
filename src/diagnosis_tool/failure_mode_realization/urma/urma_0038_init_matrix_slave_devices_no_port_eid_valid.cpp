#include "urma_0038_init_matrix_slave_devices_no_port_eid_valid.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0038InitMatrixSlaveDevicesNoPortEidValid> g_urma("urma_0038");

bool Urma0038InitMatrixSlaveDevicesNoPortEidValid::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"No port eid valid"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0038InitMatrixSlaveDevicesNoPortEidValid::GetName() const
{
    return "init_matrix_slave_devices No port eid valid";
}

std::string Urma0038InitMatrixSlaveDevicesNoPortEidValid::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!port_eid_valid`；该路径返回 -1";
}

RootCause Urma0038InitMatrixSlaveDevicesNoPortEidValid::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0038InitMatrixSlaveDevicesNoPortEidValid::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0038InitMatrixSlaveDevicesNoPortEidValid::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：No port eid valid";
}

std::string Urma0038InitMatrixSlaveDevicesNoPortEidValid::GetId() const
{
    return "urma_0038";
}
} // namespace diag
