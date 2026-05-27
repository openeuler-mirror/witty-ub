#include "urma_failure_031.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure031> g_urma("urma_031");

bool UrmaFailure031::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Uninitialized variables'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure031::GetName() const
{
    return "删除context过程中依赖步骤失败";
}

std::string UrmaFailure031::GetRootCauseDesc() const
{
    return "函数用于删除context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure031::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure031::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure031::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Uninitialized variables。";
}

std::string UrmaFailure031::GetId() const
{
    return "urma_031";
}

} // namespace diag
