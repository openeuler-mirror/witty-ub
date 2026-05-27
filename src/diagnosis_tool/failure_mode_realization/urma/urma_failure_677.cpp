#include "urma_failure_677.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure677> g_urma("urma_677");

bool UrmaFailure677::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Jfce is still used by at least one jfc, refcnt:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure677::GetName() const
{
    return "删除JFCE过程中依赖步骤失败";
}

std::string UrmaFailure677::GetRootCauseDesc() const
{
    return "函数用于删除JFCE，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure677::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure677::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure677::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfce，Jfce is still used by at least one jfc, refcnt:";
}

std::string UrmaFailure677::GetId() const
{
    return "urma_677";
}

} // namespace diag
