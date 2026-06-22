#include "urma_failure_311.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure311> g_urma("urma_311");

bool UrmaFailure311::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_vseg") != std::string::npos &&
           message.find("invalid param.") != std::string::npos;
}

std::string UrmaFailure311::GetName() const
{
    return "VSEG状态不满足要求导致删除VSEG失败";
}

std::string UrmaFailure311::GetRootCauseDesc() const
{
    return "bondp_delete_vseg执行删除VSEG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure311::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure311::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure311::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_vseg，invalid param.。";
}

std::string UrmaFailure311::GetId() const
{
    return "urma_311";
}
} // namespace diag
