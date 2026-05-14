#include "urma_failure_124.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure124> g_urma("urma_124");

bool UrmaFailure124::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_deactive_jfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfr state is wrong in deactive_jfr')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure124::GetName() const
{
    return "urma_deactive_jfr 执行激活 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure124::GetRootCauseDesc() const
{
    return "urma_deactive_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure124::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure124::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure124::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfr state is wrong in deactive_jfr";
}

std::string UrmaFailure124::GetId() const
{
    return "urma_124";
}

} // namespace diag
