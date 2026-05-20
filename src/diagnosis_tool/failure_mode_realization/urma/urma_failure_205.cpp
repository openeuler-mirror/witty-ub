#include "urma_failure_205.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure205> g_urma("urma_205");

bool UrmaFailure205::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bdp_vjfce_info_table_add' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'exist node in map'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure205::GetName() const
{
    return "bdp_vjfce_info_table_add 更新 JFCE 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure205::GetRootCauseDesc() const
{
    return "bdp_vjfce_info_table_add 需要维护 JFCE "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure205::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure205::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure205::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：exist node in map";
}

std::string UrmaFailure205::GetId() const
{
    return "urma_205";
}

} // namespace diag
