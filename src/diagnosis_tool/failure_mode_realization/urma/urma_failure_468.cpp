#include "urma_failure_468.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure468> g_urma("urma_468");

bool UrmaFailure468::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfc") != std::string::npos &&
           message.find("Jfc state is wrong in active_jfc.") != std::string::npos;
}

std::string UrmaFailure468::GetName() const
{
    return "JFC状态不满足要求导致激活JFC失败";
}

std::string UrmaFailure468::GetRootCauseDesc() const
{
    return "urma_active_jfc执行激活JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure468::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure468::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure468::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Jfc state is wrong in active_jfc.。";
}

std::string UrmaFailure468::GetId() const
{
    return "urma_468";
}
} // namespace diag
