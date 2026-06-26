#include "urma_failure_340.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure340> g_urma("urma_340");

bool UrmaFailure340::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_seg") != std::string::npos &&
           message.find("Token value must be set when token policy is not URMA_TOKEN_NONE.") != std::string::npos;
}

std::string UrmaFailure340::GetName() const
{
    return "Segment状态不满足要求导致导入Segment失败";
}

std::string UrmaFailure340::GetRootCauseDesc() const
{
    return "urma_import_seg执行导入Segment时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure340::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure340::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure340::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_seg，Token value must be set when token policy is not "
           "URMA_TOKEN_N"
           "ONE.。";
}

std::string UrmaFailure340::GetId() const
{
    return "urma_340";
}
} // namespace diag
