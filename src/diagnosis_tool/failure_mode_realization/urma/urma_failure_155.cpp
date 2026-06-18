#include "urma_failure_155.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure155> g_urma("urma_155");

bool UrmaFailure155::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_update_pjetty_id_mapping") != std::string::npos &&
           message.find("Failed to add recreated pjetty id mapping: , ret:") != std::string::npos;
}

std::string UrmaFailure155::GetName() const
{
    return "下层资源创建失败导致updateupdate、pjetty、ID失败";
}

std::string UrmaFailure155::GetRootCauseDesc() const
{
    return "bondp_update_pjetty_id_"
           "mapping在updateupdate、pjetty、ID过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure155::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure155::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure155::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_update_pjetty_id_mapping，Failed to add recreated pjetty id "
           "mapping: , r"
           "et:。";
}

std::string UrmaFailure155::GetId() const
{
    return "urma_155";
}
} // namespace diag
