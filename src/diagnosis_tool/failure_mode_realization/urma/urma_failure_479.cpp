#include "urma_failure_479.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure479> g_urma("urma_479");

bool UrmaFailure479::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_open_provider' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'realpath failed')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure479::GetName() const
{
    return "urma_open_provider 打开 provider 失败导致打开无法访问底层资源";
}

std::string UrmaFailure479::GetRootCauseDesc() const
{
    return "urma_open_provider 需要访问 provider 对应的文件、目录、provider "
           "动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider "
           "装载或上下文创建无法进行。";
}

RootCause UrmaFailure479::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure479::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure479::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：realpath failed";
}

std::string UrmaFailure479::GetId() const
{
    return "urma_479";
}

} // namespace diag
