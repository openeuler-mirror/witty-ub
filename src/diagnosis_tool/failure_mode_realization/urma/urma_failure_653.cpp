#include "urma_failure_653.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure653> g_urma("urma_653");

bool UrmaFailure653::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'resend_wr_from_node' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Unsupported send opcode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure653::GetName() const
{
    return "resend_wr_from_node 执行发送 WR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure653::GetRootCauseDesc() const
{
    return "resend_wr_from_node 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure653::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure653::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure653::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Unsupported send opcode";
}

std::string UrmaFailure653::GetId() const
{
    return "urma_653";
}

} // namespace diag
