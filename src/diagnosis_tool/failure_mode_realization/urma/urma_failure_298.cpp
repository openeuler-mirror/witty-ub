#include "urma_failure_298.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure298> g_urma("urma_298");

bool UrmaFailure298::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_grp' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jetty grp in use, jetty_cnt:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure298::GetName() const
{
    return "删除Jetty过程中依赖步骤失败";
}

std::string UrmaFailure298::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure298::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure298::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure298::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty_grp，jetty grp in use, jetty_cnt:。";
}

std::string UrmaFailure298::GetId() const
{
    return "urma_298";
}

} // namespace diag
