#include "urma_failure_605.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure605> g_urma("urma_605");

bool UrmaFailure605::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_scan_sysfs_devices") != std::string::npos &&
           message.find("Failed close dir:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure605::GetName() const
{
    return "scanSCAN、sysfs信息、devices执行失败导致scanSCAN、sysfs信息、devices失败";
}

std::string UrmaFailure605::GetRootCauseDesc() const
{
    return "urma_scan_sysfs_"
           "devices执行scanSCAN、sysfs信息、devices时依赖的scanSCAN、sysfs信息、devices步骤返回错误，当前URMA操作无法继"
           "续完成。";
}

RootCause UrmaFailure605::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure605::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure605::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_scan_sysfs_devices，Failed close dir:，, errno:。";
}

std::string UrmaFailure605::GetId() const
{
    return "urma_605";
}
} // namespace diag
