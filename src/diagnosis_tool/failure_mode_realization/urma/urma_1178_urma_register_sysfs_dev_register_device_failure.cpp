#include "urma_1178_urma_register_sysfs_dev_register_device_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure> g_urma("urma_1178");

bool Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Register device failed. Failed to match driver for device %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::GetName() const
{
    return "urma_register_sysfs_dev 注册设备失败";
}

std::string Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Register device failed. Failed to match driver for device %.";
}

std::string Urma1178UrmaRegisterSysfsDevRegisterDeviceFailure::GetId() const
{
    return "urma_1178";
}
} // namespace diag
