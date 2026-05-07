// failure_mode_factory.cpp
#include "failure_mode_factory.h"
#include <iostream>
#include "failure_mode.h"

namespace diag {

FailureModeFactory &FailureModeFactory::Instance()
{
    static FailureModeFactory instance;
    return instance;
}

void FailureModeFactory::Register(const std::string &typeId, Creator creator) noexcept
{
    try {
        std::cout << "Register: " << typeId << std::endl;
        m_creators[typeId] = std::move(creator);
    } catch (...) {
        // 注册失败，但不抛异常
        std::terminate();
    }
    
}

std::shared_ptr<FailureMode> FailureModeFactory::Create(const std::string &typeId) const
{
    auto it = m_creators.find(typeId);
    if (it != m_creators.end()) {
        return it->second();
    }
    std::cout << "nullptr" << std::endl;
    return nullptr;
}

std::vector<std::string> FailureModeFactory::GetAllTypeIds() const
{
    std::vector<std::string> ids;
    ids.reserve(m_creators.size());
    for (const auto &[id, _] : m_creators) {
        ids.push_back(id);
    }
    return ids;
}

bool FailureModeFactory::IsRegistered(const std::string &typeId) const
{
    return m_creators.find(typeId) != m_creators.end();
}

} // namespace diag