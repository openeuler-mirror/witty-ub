#include "urma_failure_824.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure824> g_urma("urma_824");

bool UrmaFailure824::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_close_provider' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'close failed, err'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure824::GetName() const
{
    return "urma_close_provider 打开 provider 失败导致处理无法访问底层资源";
}

std::string UrmaFailure824::GetRootCauseDesc() const
{
    return "urma_close_provider 需要访问 provider 对应的文件、目录、provider "
           "动态库或字符设备，但路径不存在、权限不足或系统调用失败，导致后续 URMA 设备枚举、provider "
           "装载或上下文创建无法进行。";
}

RootCause UrmaFailure824::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure824::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure824::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：close failed, err";
}

std::string UrmaFailure824::GetId() const
{
    return "urma_824";
}

} // namespace diag
