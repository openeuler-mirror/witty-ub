#include "urma_failure_307.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure307> g_urma("urma_307");

bool UrmaFailure307::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vcontext") != std::string::npos &&
           message.find("Failed to create remote_v2p_token_id_table") != std::string::npos;
}

std::string UrmaFailure307::GetName() const
{
    return "下层资源创建失败导致创建vcontext失败";
}

std::string UrmaFailure307::GetRootCauseDesc() const
{
    return "bondp_create_vcontext在创建vcontext过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure307::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure307::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure307::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vcontext，Failed to create remote_v2p_token_id_table。";
}

std::string UrmaFailure307::GetId() const
{
    return "urma_307";
}
} // namespace diag
