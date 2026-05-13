#include "urma_1175_urma_create_context_cdev_device_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1175UrmaCreateContextCdevDeviceFailure> g_urma("urma_1175");

bool Urma1175UrmaCreateContextCdevDeviceFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to open urma cdev with path %, dev_fd: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1175UrmaCreateContextCdevDeviceFailure::GetName() const
{
    return "urma_create_context 打开cdev设备失败";
}

std::string Urma1175UrmaCreateContextCdevDeviceFailure::GetRootCauseDesc() const
{
    return "目标文件、设备节点或动态库打开失败，可能由于路径不存在、权限不足或 provider/设备文件不可访问；该路径返回 "
           "NULL";
}

RootCause Urma1175UrmaCreateContextCdevDeviceFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1175UrmaCreateContextCdevDeviceFailure::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma1175UrmaCreateContextCdevDeviceFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to open urma cdev with path %, dev_fd: %";
}

std::string Urma1175UrmaCreateContextCdevDeviceFailure::GetId() const
{
    return "urma_1175";
}
} // namespace diag
