#include "urma_0973_urma_query_device_attr_get_cdev_path_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0973UrmaQueryDeviceAttrGetCdevPathFailure> g_urma("urma_0973");

bool Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get cdev_path, dev_name: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::GetName() const
{
    return "urma_query_device_attr 获取cdev路径失败";
}

std::string Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `snprintf(cdev_path, URMA_MAX_PATH, \"%/%\", URMA_DEV_PATH, sysfs_dev->dev_name) <= "
           "0`；该路径返回 -1";
}

RootCause Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get cdev_path, dev_name: %.";
}

std::string Urma0973UrmaQueryDeviceAttrGetCdevPathFailure::GetId() const
{
    return "urma_0973";
}
} // namespace diag
