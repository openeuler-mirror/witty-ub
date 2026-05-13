#include "urma_0969_urma_ioctl_get_eid_list_cdev_device_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0969UrmaIoctlGetEidListCdevDeviceFailure> g_urma("urma_0969");

bool Urma0969UrmaIoctlGetEidListCdevDeviceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to open urma cdev with path %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0969UrmaIoctlGetEidListCdevDeviceFailure::GetName() const
{
    return "urma_ioctl_get_eid_list 打开cdev设备失败";
}

std::string Urma0969UrmaIoctlGetEidListCdevDeviceFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "-1";
}

RootCause Urma0969UrmaIoctlGetEidListCdevDeviceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0969UrmaIoctlGetEidListCdevDeviceFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0969UrmaIoctlGetEidListCdevDeviceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to open urma cdev with path %";
}

std::string Urma0969UrmaIoctlGetEidListCdevDeviceFailure::GetId() const
{
    return "urma_0969";
}
} // namespace diag
