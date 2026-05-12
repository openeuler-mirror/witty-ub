#include "urma_0037_init_matrix_slave_devices_primary_eid_is_empty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty> g_urma("urma_0037");

bool Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Primary eid % is empty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::GetName() const
{
    return "init_matrix_slave_devices Primary eid % is empty";
}

std::string Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `is_empty_eid(eid_list[i])`；该路径返回 -1";
}

RootCause Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Primary eid % is empty";
}

std::string Urma0037InitMatrixSlaveDevicesPrimaryEidIsEmpty::GetId() const
{
    return "urma_0037";
}
} // namespace diag
