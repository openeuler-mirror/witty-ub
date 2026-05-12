#include "urma_0986_urma_get_device_name_invalid_dev_name.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0986UrmaGetDeviceNameInvalidDevName> g_urma("urma_0986");

bool Urma0986UrmaGetDeviceNameInvalidDevName::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid dev_name."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0986UrmaGetDeviceNameInvalidDevName::GetName() const
{
    return "urma_get_device_by_name Invalid dev_name.";
}

std::string Urma0986UrmaGetDeviceNameInvalidDevName::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `dev_name == NULL || strnlen(dev_name, URMA_MAX_NAME) >= URMA_MAX_NAME`；该路径返回 "
           "NULL";
}

RootCause Urma0986UrmaGetDeviceNameInvalidDevName::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0986UrmaGetDeviceNameInvalidDevName::GetFixSuggDesc() const
{
    return "```\nlsmod | grep udma\nurma_admin show -a // 查看UB设备是否存在，部署完成后重试\n```";
}

std::string Urma0986UrmaGetDeviceNameInvalidDevName::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid dev_name.";
}

std::string Urma0986UrmaGetDeviceNameInvalidDevName::GetId() const
{
    return "urma_0986";
}
} // namespace diag
