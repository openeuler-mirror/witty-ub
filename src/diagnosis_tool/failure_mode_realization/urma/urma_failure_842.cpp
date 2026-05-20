#include "urma_failure_842.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure842> g_urma("urma_842");

bool UrmaFailure842::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_del_jetty_p_vjetty_info_without_lock' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete p_vjetty_id node: ret:' | "
        "grep -F 'pjetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure842::GetName() const
{
    return "bondp_del_jetty_p_vjetty_info_without_lock 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure842::GetRootCauseDesc() const
{
    return "bondp_del_jetty_p_vjetty_info_without_lock 调用下层 provider、bond 组件或系统接口处理 Jetty "
           "时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure842::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure842::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure842::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete p_vjetty_id node: ret: pjetty_id";
}

std::string UrmaFailure842::GetId() const
{
    return "urma_842";
}

} // namespace diag
