#include "urma_0976_urma_read_sysfs_device_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0976UrmaReadSysfsDevicePathFailure> g_urma("urma_0976");

bool Urma0976UrmaReadSysfsDevicePathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"snprintf failed, dev_name: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0976UrmaReadSysfsDevicePathFailure::GetName() const
{
    return "urma_read_sysfs_device 格式化路径失败";
}

std::string Urma0976UrmaReadSysfsDevicePathFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误";
}

RootCause Urma0976UrmaReadSysfsDevicePathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0976UrmaReadSysfsDevicePathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0976UrmaReadSysfsDevicePathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：snprintf failed, dev_name: %.";
}

std::string Urma0976UrmaReadSysfsDevicePathFailure::GetId() const
{
    return "urma_0976";
}
} // namespace diag
