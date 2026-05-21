#include "urma_failure_647.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure647> g_urma("urma_647");

bool UrmaFailure647::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_post_send_wr_no_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Bondp supports at most wr_list'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure647::GetName() const
{
    return "bondp_post_send_wr_no_store 执行投递 WR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure647::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_no_store 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure647::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure647::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure647::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Bondp supports at most wr_list";
}

std::string UrmaFailure647::GetId() const
{
    return "urma_647";
}

} // namespace diag
