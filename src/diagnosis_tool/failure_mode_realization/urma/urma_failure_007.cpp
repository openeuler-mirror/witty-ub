#include "urma_failure_007.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure007> g_urma("urma_007");

bool UrmaFailure007::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vjfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'bondp init jfr fail:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure007::GetName() const
{
    return "初始化JFR过程中依赖步骤失败";
}

std::string UrmaFailure007::GetRootCauseDesc() const
{
    return "函数用于初始化JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure007::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure007::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure007::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjfr，bondp init jfr fail:。";
}

std::string UrmaFailure007::GetId() const
{
    return "urma_007";
}

} // namespace diag
