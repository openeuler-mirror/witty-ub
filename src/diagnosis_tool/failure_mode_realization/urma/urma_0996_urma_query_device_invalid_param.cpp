#include "urma_0996_urma_query_device_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0996UrmaQueryDeviceInvalidParam> g_urma("urma_0996");

bool Urma0996UrmaQueryDeviceInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0996UrmaQueryDeviceInvalidParam::GetName() const
{
    return "urma_query_device 参数非法";
}

std::string Urma0996UrmaQueryDeviceInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dev == NULL || dev->sysfs_dev == NULL || dev_attr == NULL`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0996UrmaQueryDeviceInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0996UrmaQueryDeviceInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0996UrmaQueryDeviceInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0996UrmaQueryDeviceInvalidParam::GetId() const
{
    return "urma_0996";
}
} // namespace diag
