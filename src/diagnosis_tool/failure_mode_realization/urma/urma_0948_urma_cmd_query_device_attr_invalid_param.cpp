#include "urma_0948_urma_cmd_query_device_attr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0948UrmaCmdQueryDeviceAttrInvalidParam> g_urma("urma_0948");

bool Urma0948UrmaCmdQueryDeviceAttrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0948UrmaCmdQueryDeviceAttrInvalidParam::GetName() const
{
    return "urma_cmd_query_device_attr 参数非法";
}

std::string Urma0948UrmaCmdQueryDeviceAttrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dev_fd < 0 || sysfs_dev == NULL`；该路径返回 -1";
}

RootCause Urma0948UrmaCmdQueryDeviceAttrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0948UrmaCmdQueryDeviceAttrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0948UrmaCmdQueryDeviceAttrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0948UrmaCmdQueryDeviceAttrInvalidParam::GetId() const
{
    return "urma_0948";
}
} // namespace diag
