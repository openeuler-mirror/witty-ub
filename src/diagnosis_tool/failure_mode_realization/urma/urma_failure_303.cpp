#include "urma_failure_303.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure303> g_urma("urma_303");

bool UrmaFailure303::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'deepcopy_jfr_wr_node' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Deepcopy sg failed'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure303::GetName() const
{
    return "deepcopy_jfr_wr_node 执行复制 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure303::GetRootCauseDesc() const
{
    return "deepcopy_jfr_wr_node 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure303::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure303::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure303::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Deepcopy sg failed";
}

std::string UrmaFailure303::GetId() const
{
    return "urma_303";
}

} // namespace diag
