#include "urma_failure_480.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure480> g_urma("urma_480");

bool UrmaFailure480::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_open_provider' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'open failed, err')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure480::GetName() const
{
    return "urma_open_provider 打开 provider 失败导致打开无法访问底层资源";
}

std::string UrmaFailure480::GetRootCauseDesc() const
{
    return "urma_open_provider 需要访问 provider 对应的文件、目录、provider "
           "动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider "
           "装载或上下文创建无法进行。";
}

RootCause UrmaFailure480::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure480::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure480::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：open failed, err";
}

std::string UrmaFailure480::GetId() const
{
    return "urma_480";
}

} // namespace diag
