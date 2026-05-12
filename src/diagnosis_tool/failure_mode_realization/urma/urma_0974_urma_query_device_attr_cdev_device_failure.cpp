#include "urma_0974_urma_query_device_attr_cdev_device_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0974UrmaQueryDeviceAttrCdevDeviceFailure> g_urma("urma_0974");

bool Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to open urma cdev, path %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::GetName() const
{
    return "urma_query_device_attr 打开cdev设备失败";
}

std::string Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to open urma cdev, path %.";
}

std::string Urma0974UrmaQueryDeviceAttrCdevDeviceFailure::GetId() const
{
    return "urma_0974";
}
} // namespace diag
