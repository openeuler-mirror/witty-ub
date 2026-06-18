#include "urma_failure_570.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure570> g_urma("urma_570");

bool UrmaFailure570::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfs") != std::string::npos &&
           message.find("jfs state is wrong in deactive_jfs.") != std::string::npos;
}

std::string UrmaFailure570::GetName() const
{
    return "JFS状态不满足要求导致去激活JFS失败";
}

std::string UrmaFailure570::GetRootCauseDesc() const
{
    return "urma_deactive_jfs执行去激活JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure570::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure570::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure570::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfs，jfs state is wrong in deactive_jfs.。";
}

std::string UrmaFailure570::GetId() const
{
    return "urma_570";
}
} // namespace diag
