#include "urma_failure_872.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure872> g_urma("urma_872");

bool UrmaFailure872::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfr_wr_inner' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to copy in wr->next')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure872::GetName() const
{
    return "deepcopy_jfr_wr_inner 执行复制 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure872::GetRootCauseDesc() const
{
    return "deepcopy_jfr_wr_inner 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure872::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure872::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure872::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to copy in wr->next";
}

std::string UrmaFailure872::GetId() const
{
    return "urma_872";
}

} // namespace diag
