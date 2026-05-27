#include "urma_failure_046.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure046> g_urma("urma_046");

bool UrmaFailure046::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'urma_init has been called before.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure046::GetName() const
{
    return "初始化URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure046::GetRootCauseDesc() const
{
    return "函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次U"
           "RMA操作失败。";
}

RootCause UrmaFailure046::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure046::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string UrmaFailure046::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_init，urma_init has been called before.";
}

std::string UrmaFailure046::GetId() const
{
    return "urma_046";
}

} // namespace diag
