#include "urma_failure_199.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure199> g_urma("urma_199");

bool UrmaFailure199::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add jetty id to p_vjetty_id table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure199::GetName() const
{
    return "bondp_create_jetty 更新 context 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure199::GetRootCauseDesc() const
{
    return "bondp_create_jetty 需要维护 context "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure199::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure199::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure199::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add jetty id to p_vjetty_id table";
}

std::string UrmaFailure199::GetId() const
{
    return "urma_199";
}

} // namespace diag
