#include "urma_failure_514.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure514> g_urma("urma_514");

bool UrmaFailure514::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_update_pjetty_id_mapping") != std::string::npos &&
           message.find("Failed to delete stale pjetty id mapping: , ret:") != std::string::npos;
}

std::string UrmaFailure514::GetName() const
{
    return "下层资源删除失败导致updateupdate、pjetty、ID失败";
}

std::string UrmaFailure514::GetRootCauseDesc() const
{
    return "bondp_update_pjetty_id_"
           "mapping清理update、pjetty、ID时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure514::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure514::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure514::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_update_pjetty_id_mapping，Failed to delete stale pjetty id "
           "mapping: , re"
           "t:。";
}

std::string UrmaFailure514::GetId() const
{
    return "urma_514";
}
} // namespace diag
