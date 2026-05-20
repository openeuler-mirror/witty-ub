#include "urma_failure_775.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure775> g_urma("urma_775");

bool UrmaFailure775::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure775::GetName() const
{
    return "urma_free_jfr 执行释放 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure775::GetRootCauseDesc() const
{
    return "urma_free_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure775::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure775::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure775::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfr still actived, please deactived first";
}

std::string UrmaFailure775::GetId() const
{
    return "urma_775";
}

} // namespace diag
