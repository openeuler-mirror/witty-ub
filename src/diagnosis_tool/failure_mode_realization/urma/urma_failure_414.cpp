#include "urma_failure_414.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure414> g_urma("urma_414");

bool UrmaFailure414::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_query_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'query pjfr fail, index:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure414::GetName() const
{
    return "查询物理 JFR过程中依赖步骤失败";
}

std::string UrmaFailure414::GetRootCauseDesc() const
{
    return "函数用于查询物理 "
           "JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure414::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure414::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure414::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_query_jfr，query pjfr fail, index:，, ret:。";
}

std::string UrmaFailure414::GetId() const
{
    return "urma_414";
}

} // namespace diag
